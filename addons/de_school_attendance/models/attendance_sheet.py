# -*- coding: utf-8 -*-

from babel.dates import format_date
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AttendanceSheet(models.Model):
    _name = "oe.attendance.sheet"
    _description = "Attendance Sheet"
    _order = "name asc"

    READONLY_STATES = {
        'progress': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    name = fields.Char(string='Name', required=True, index='trigram', translate=True,  states=READONLY_STATES,)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('progress', 'Attendance Start'),
        ('done', 'Attendance Taken'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company, states=READONLY_STATES,)
    student_attendance_mode = fields.Selection(related='company_id.student_attendance_mode')
    date = fields.Date(string='Date', required=True, states=READONLY_STATES,)
    check_in = fields.Datetime(string="Check In", default=fields.Datetime.now, states=READONLY_STATES,)
    check_out = fields.Datetime(string="Check Out", states=READONLY_STATES,)
    
    attendance_register_id = fields.Many2one('oe.attendance.register', string='Attendance Register', required=True, states=READONLY_STATES,)
    course_id = fields.Many2one('oe.school.course', related='attendance_register_id.course_id')
    batch_id = fields.Many2one('oe.school.course.batch', string='Batch', required=True, states=READONLY_STATES,)
    subject_id = fields.Many2one('oe.school.subject', string='Subject', 
                                 
                                 states=READONLY_STATES,)
    description = fields.Html(string='Description')

    sheet_to_close = fields.Boolean(string='Sheet to Close', compute='_compute_sheet_to_close')
    attendance_sheet_line = fields.One2many('oe.attendance.sheet.line', 'attendance_sheet_id', 
                        states={'draft': [('readonly', False)], 'progress': [('readonly', False)]},
                        readonly=True, string='Sheet Lines')
    _sql_constraints = [
        ('unique_date_attendance_register', 'unique(date, attendance_register_id)', 
         'Attendance has already been marked for the given date.'
        ),
    ]

    @api.depends('state','attendance_sheet_line')
    def _compute_sheet_to_close(self):
        for record in self:
            if record.state == 'progress':
                if len(record.attendance_sheet_line) > 0:
                    record.sheet_to_close = True
                else:
                    record.sheet_to_close = False
            else:
                record.sheet_to_close = False
        
    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise exceptions.UserError("You cannot delete a record with the status is not 'Draft'.")
        return super(YourModel, self).unlink()

    def button_draft(self):
        self.write({'state': 'draft'})

    def button_open(self):
        self.write({'state': 'progress'})

    def button_close(self):
        for line in self.attendance_sheet_line:
            vals = {
                'student_id': line.student_id.id,
                'attendance_status': line.attendance_status,
                'is_late_arrival': line.is_late_arrival,
                'attendance_sheet_id': line.attendance_sheet_id.id,
                'date_attendance': self.date,
                'company_id': self.company_id,
            }
            if self.student_attendance_mode == 'period':
                vals['check_in'] = self.check_in
                vals['check_out'] = self.check_out
            else:
                vals['check_in'] = self.date
            self.env['oe.student.attendance'].create(vals)
        self.write({'state': 'done'})
        
    def button_cancel(self):
        self.write({'state': 'draft'})

    def button_mark_attendance(self):
        self.ensure_one()
        #raise UserError(self.id)
        
        action = {
            'name': _('Mark Attendance'),
            'res_model': 'oe.attendance.mark.wizard',
            'view_mode': 'form',
            'context': {
                'active_model': 'oe.attendance.sheet',
                'active_ids': self.ids,
                'active_id': self.id,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }
        return action

class AttendanceSheet(models.Model):
    _name = "oe.attendance.sheet.line"
    _description = "Attendance Sheet Line"
    _order = "student_id asc"

    attendance_sheet_id = fields.Many2one('oe.attendance.sheet', string='Attendance Sheet')
    student_id = fields.Many2one('res.partner', string="Student", 
                                 domain="[('is_student','=',True)]",
                                 required=True, ondelete='cascade', index=True)
    attendance_status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
    ], string='Attendance Type', default='present')
    is_late_arrival = fields.Boolean(string='Late Arrival')
                                 
    