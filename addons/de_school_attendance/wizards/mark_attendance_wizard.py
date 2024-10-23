# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AttendanceMarkWizard(models.TransientModel):
    _name = 'oe.attendance.mark.wizard'
    _description = 'Mark Student Attendance'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id, index=True, readonly=False)

    attendance_sheet_id = fields.Many2one('oe.attendance.sheet',string="Attendance Sheet", readonly=True )
    attendance_status = fields.Selection([
        ('absent', 'Mark Absent'),
        ('present', 'Mark Present'),
    ], string='Attendance Type', default='absent', required=True)

    is_late_arrival = fields.Boolean(string='Late Arrival')
    student_ids = fields.Many2many('res.partner',
        relation='oe_attendance_mark_wizard_students_rel',
        column1='wizard_id',
        column2='student_id',
        domain="[('is_student','=',True)]",
        string='Students'
    )

    
    @api.model
    def default_get(self, fields):
        res = super(AttendanceMarkWizard, self).default_get(fields)
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id', [])
        record = self.env[active_model].search([('id','=',active_id)])
        #raise UserError(record.name)
        res['attendance_sheet_id'] = record.id
        #self.attendance_sheet_id = record.id
        return res

    
    def _compute_from_attedance_register(self):
        for record in self:
            record.course_id = record.attendance_register_id.course_id.id

    
    def action_process_attendance(self):
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids', [])
        active_id = self.env.context.get('active_id', [])
        record_id = self.env[active_model].search([('id','=',active_id)])

        student_ids = self.env['res.partner'].search([('course_id','=',record_id.course_id.id),('batch_id','=',record_id.batch_id.id),('is_student','=',True)])
        rem_student_ids = student_ids - self.student_ids
        attendance_values = []
        # If mode_attendance is 'absent', create records for selected students with 'absent' flag
        if self.attendance_status == 'absent':
            for student in self.student_ids:
                attendance_values.append({
                    'student_id': student.id,
                    'attendance_status': 'absent',
                    'attendance_sheet_id': record_id.id,
                })
            for student in rem_student_ids:
                attendance_values.append({
                    'student_id': student.id,
                    'attendance_status': 'present',
                    'attendance_sheet_id': record_id.id,
                })
            if len(record_id.attendance_sheet_line):
                record_id.attendance_sheet_line.unlink()
            #record_id.attendance_sheet_line.create(attendance_values)
            #raise UserError(active_model)
            self.env['oe.attendance.sheet.line'].create(attendance_values)
        
    