# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import datetime, timedelta, time
from operator import itemgetter

import pytz
from odoo import models, fields, api, exceptions, _
from odoo.tools import format_datetime
from odoo.osv.expression import AND, OR
from odoo.tools.float_utils import float_is_zero
from odoo.exceptions import UserError, ValidationError


class StudentAttendance(models.Model):
    _name = "oe.student.attendance"
    _description = "Student Attendance"
    _order = "check_in desc"


    student_id = fields.Many2one('res.partner', string="Student", 
                                 domain="[('is_student','=',True)]",
                                 required=True, ondelete='cascade', index=True)
    date_attendance = fields.Date('Attendance Date', required=True)
    check_in = fields.Datetime(string="Check In", compute='_compute_check_in', readonly=False, store=True)
    check_out = fields.Datetime(string="Check Out")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    student_attendance_mode = fields.Selection(related='company_id.student_attendance_mode')

    attendance_hours = fields.Float(string='Attendance Hours', compute='_compute_attendance_hours', store=True, readonly=True)

    attendance_status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
    ], string='Attendance Type', default='present')
    is_late_arrival = fields.Boolean(string='Late Arrival')
    
    attendance_sheet_id = fields.Many2one('oe.attendance.sheet', string='Attendance Sheet')

    #Academic Fields
    course_id = fields.Many2one('oe.school.course', store=True, 
                                compute='_compute_from_student_id'
                               )
    roll_no = fields.Char(string='Roll No.', store=True, compute='_compute_from_student_id')
    batch_id = fields.Many2one('oe.school.course.batch', related='student_id.batch_id')

    #period wise attendance fields
    subject_id = fields.Many2one('oe.school.subject', string='Subject',
                                 domain="[('id','in',subject_ids)]"
                                )
    subject_ids = fields.Many2many('oe.school.subject', string='Subjects', compute='_compute_subject_ids', store=True)
    
    # ----------------------------------------
    # Constraints
    # ----------------------------------------
    @api.constrains('student_id', 'date_attendance')
    def _check_student_attendance_overlap(self):
        for record in self:
            if record.student_attendance_mode == 'period':
                # Check if there are any overlapping records with the same student and date_attendance
                domain = [
                    ('student_id', '=', record.student_id.id),
                    ('date_attendance', '=', record.date_attendance),
                    ('id', '!=', record.id),
                    '|',
                    ('check_in', '<=', record.check_in),
                    ('check_out', '>=', record.check_in),
                ]
            else:
                # Check if there are any overlapping records with the same student and date_attendance
                domain = [
                    ('student_id', '=', record.student_id.id),
                    ('date_attendance', '=', record.date_attendance),
                    ('id', '!=', record.id),
                ]
            
            if self.search_count(domain) > 0:
                raise exceptions.ValidationError(_('Student attendance cannot overlap.'))

    @api.constrains('subject_id')
    def _check_subject_id(self):
        for record in self:
            if record.company_id.student_attendance_mode == 'period' and not record.subject_id:
                raise exceptions.ValidationError("Please select a subject.")

    @api.constrains('check_in', 'date_attendance')
    def _check_check_in_date(self):
        for attendance in self:
            if attendance.check_in:
                if attendance.check_in.date() != attendance.date_attendance:
                    raise ValidationError("Check In date must match the Attendance Date.")

    
    # ----------------------------------------
    # Compute Methods
    # ----------------------------------------
    @api.depends('check_in', 'check_out')
    def _compute_attendance_hours(self):
        for attendance in self:
            if attendance.check_out and attendance.check_in:
                delta = attendance.check_out - attendance.check_in
                attendance.attendance_hours = delta.total_seconds() / 3600.0
            else:
                attendance.attendance_hours = False

    @api.depends('student_id')
    def _compute_from_student_id(self):
        for record in self:
            record.course_id = record.student_id.course_id.id
            record.roll_no = record.student_id.roll_no


    @api.depends('date_attendance')
    def _compute_check_in(self):
        for attendance in self:
            if attendance.date_attendance:
                attendance.check_in = datetime.combine(attendance.date_attendance, time(9, 0))
            else:
                attendance.check_in = False

    def _company_calendar_timezone(self, original_dt):
        """
        Convert the given datetime to the specified target time zone.
        
        :param original_dt: The original datetime object to be converted.
        :param target_timezone: The target time zone (e.g., 'Asia/Karachi').
        :return: A new datetime object in the target time zone.
        """
        # Create a time zone object for the target time zone
        target_tz = pytz.timezone(self.company_id.resource_calendar_id.tz)
    
        # Localize the original datetime to the target time zone
        localized_dt = original_dt.astimezone(target_tz)
        
        return localized_dt

    @api.depends('course_id')
    def _compute_subject_ids(self):
        for attendance in self:
            if attendance.course_id:
                subject_lines = attendance.env['oe.school.course.subject.line'].search([
                    ('course_id', '=', attendance.course_id.id)
                ])
                attendance.subject_ids = subject_lines.mapped('subject_id')
            else:
                attendance.subject_ids = False


