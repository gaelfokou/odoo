from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from pprint import pformat
import pandas as pd
import numpy as np
import re
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import copy
import pytz
import logging

UTC_TZ = pytz.utc

DATE_FORMAT = '%Y-%m-%d'
DATE_FORMAT_FR = '%d/%m/%Y'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATETIME_FORMAT_FR = '%d/%m/%Y %H:%M'
TIME_FORMAT = '%H:%M:%S'
TIME_FORMAT_FR = '%H:%M'

ATTENDANCE_TYPE = {
    '0': 'Type_0',
    '1': 'Finger',
    '2': 'Type_2',
    '3': 'Password',
    '4': 'Card',
    '15': 'Face',
}

PUNCH_TYPE = {
    '0': 'Check In',
    '1': 'Check Out',
    '2': 'Break Out',
    '3': 'Break In',
    '4': 'Overtime In',
    '5': 'Overtime Out',
}

_logger = logging.getLogger(__name__)

class DailyAttendanceFilterWizard(models.TransientModel):
    _name = 'daily.attendance.filter.wizard'
    _description = 'Filtre des présences'

    employee_id = fields.Many2one('hr.employee', string='Employee',
                                  help='Employee Name')
    start_punching_day = fields.Datetime(string='Start Date', help='Start date of punching')
    end_punching_day = fields.Datetime(string='End Date', help='End date of punching')
    address_id = fields.Many2one('res.partner', string='Working Address',
                                 help='Working address of the employee')
    attendance_type = fields.Selection([('1', 'Finger'), ('15', 'Face'),
                                        ('2', 'Type_2'), ('3', 'Password'),
                                        ('0', 'Type_0'), ('4', 'Card')], string='Category',
                                       help='Attendance detecting methods')
    punch_type = fields.Selection([('0', 'Check In'), ('1', 'Check Out'),
                                   ('2', 'Break Out'), ('3', 'Break In'),
                                   ('4', 'Overtime In'), ('5', 'Overtime Out')],
                                  string='Punching Type',
                                  help='The Punching Type of attendance')
    start_punching_time = fields.Datetime(string='Start Punching Time',
                                    help='Start punching time in the device')
    end_punching_time = fields.Datetime(string='End Punching Time',
                                    help='End punching time in the device')

    @api.constrains('start_punching_day', 'end_punching_day')
    def _constrains_punching_day(self):
        for record in self:
            if record.end_punching_day < record.start_punching_day:
                raise ValidationError("La date de fin doit être supérieure à la date de début")

    @api.constrains('start_punching_time', 'end_punching_time')
    def _constrains_punching_time(self):
        for record in self:
            if record.end_punching_time < record.start_punching_time:
                raise ValidationError("La date de fin doit être supérieure à la date de début")

    @staticmethod
    def convert_datetime_from_utc(dt):
        new_tz = pytz.timezone('Africa/Douala')
        old_tz = pytz.utc
        local_dt = old_tz.localize(dt)
        dt = local_dt.astimezone(new_tz)
        return dt

    @staticmethod
    def convert_datetime_to_utc(dt):
        old_tz = pytz.timezone('Africa/Douala')
        new_tz = pytz.utc
        local_dt = old_tz.localize(dt)
        dt = local_dt.astimezone(new_tz)
        return dt

    def action_filter(self):
        domain = []
        title = []
        if self.employee_id.id:
            domain.append(('employee_id', '=', self.employee_id.id))
            title.append(self.employee_id.name)
        if self.address_id.id:
            domain.append(('address_id', '=', self.address_id.id))
            title.append(self.address_id.name)
        if self.attendance_type:
            domain.append(('attendance_type', '=', self.attendance_type))
            title.append(ATTENDANCE_TYPE[self.attendance_type])
        if self.punch_type:
            domain.append(('punch_type', '=', self.punch_type))
            title.append(PUNCH_TYPE[self.punch_type])

        attendance_ids = []
        attendances = self.env['daily.attendance'].search(domain)
        if self.start_punching_day and self.end_punching_day:
            datetime_before = DailyAttendanceFilterWizard.convert_datetime_to_utc(self.start_punching_day)
            datetime_after = DailyAttendanceFilterWizard.convert_datetime_to_utc(self.end_punching_day)
            start_punching_day = datetime.strftime(self.start_punching_day, DATE_FORMAT_FR)
            end_punching_day = datetime.strftime(self.end_punching_day, DATE_FORMAT_FR)
            title.append('Date')
            title.append('{} - {}'.format(start_punching_day, end_punching_day))
            attendances = attendances.filtered(lambda rec: UTC_TZ.localize(rec.punching_day) >= datetime_before and UTC_TZ.localize(rec.punching_day) <= datetime_after)
        if self.start_punching_time and self.end_punching_time:
            datetime_before = DailyAttendanceFilterWizard.convert_datetime_to_utc(self.start_punching_time)
            datetime_after = DailyAttendanceFilterWizard.convert_datetime_to_utc(self.end_punching_time)
            start_punching_time = datetime.strftime(self.start_punching_time, DATE_FORMAT_FR)
            end_punching_time = datetime.strftime(self.end_punching_time, DATE_FORMAT_FR)
            title.append('Punching Time')
            title.append('{} - {}'.format(start_punching_time, end_punching_time))
            attendances = attendances.filtered(lambda rec: UTC_TZ.localize(rec.punching_time) >= datetime_before and UTC_TZ.localize(rec.punching_time) <= datetime_after)
        for attendance in attendances:
            attendance_ids.append(attendance.id)
        attendance_ids = list(set(attendance_ids))

        domain = [
            ('id', 'in', attendance_ids)
        ]

        if len(title) > 0:
            title = ' / '.join(title)
        else:
            title = 'Non spécifié'

        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', title)

        view_id = self.env.ref('hr_zk_attendance.daily_attendance_view_tree').id
        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'daily.attendance',
            'views': [(view_id, 'tree'), (False, 'form')],
            'view_id': view_id,
            'domain' : domain,
            'target': 'main',
        }
