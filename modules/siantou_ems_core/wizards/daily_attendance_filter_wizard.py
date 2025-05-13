from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from pprint import pformat
import pandas as pd
import numpy as np
import re
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import copy
import logging

DATE_FORMAT = '%Y-%m-%d'
DATE_FORMAT_FR = '%d/%m/%Y'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATETIME_FORMAT_FR = '%d/%m/%Y %H:%M'
TIME_FORMAT = '%H:%M:%S'
TIME_FORMAT_FR = '%H:%M'

ATTENDANCE_TYPE = {
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
    punching_day = fields.Datetime(string='Date', help='Date of punching')
    address_id = fields.Many2one('res.partner', string='Working Address',
                                 help='Working address of the employee')
    attendance_type = fields.Selection([('1', 'Finger'), ('15', 'Face'),
                                        ('2', 'Type_2'), ('3', 'Password'),
                                        ('4', 'Card')], string='Category',
                                       help='Attendance detecting methods')
    punch_type = fields.Selection([('0', 'Check In'), ('1', 'Check Out'),
                                   ('2', 'Break Out'), ('3', 'Break In'),
                                   ('4', 'Overtime In'), ('5', 'Overtime Out')],
                                  string='Punching Type',
                                  help='The Punching Type of attendance')
    punching_time = fields.Datetime(string='Punching Time',
                                    help='Punching time in the device')

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
        if self.punching_day:
            domain.append(('punching_day', '=', self.punching_day))
            title.append(datetime.strftime(self.punching_day, DATE_FORMAT_FR))
        if self.punching_time:
            domain.append(('punching_time', '=', self.punching_time))
            title.append(datetime.strftime(self.punching_time, DATE_FORMAT_FR))

        attendance_ids = []
        attendances = self.env['daily.attendance'].search(domain)
        for attendance in attendances:
            attendance_ids.append(attendance.id)
        attendance_ids = list(set(attendance_ids))

        domain = [('id', 'in', attendance_ids)]

        if len(title) > 0:
            title = '/'.join(title)
        else:
            title = 'Non spécifié'

        self.env['ir.config_parameter'].sudo().set_param(f'filter.{self.env.user.id}', title)

        view_id = self.env.ref('siantou_ems_core.attendance_tree_view').id
        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'daily.attendance',
            'views': [(view_id, 'tree')],
            'view_id': view_id,
            'domain' : domain,
            'target': 'main',
        }
