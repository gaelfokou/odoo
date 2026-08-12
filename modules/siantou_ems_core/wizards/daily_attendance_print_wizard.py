# -*- coding: utf-8 -*-

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


class TeacherPrintWizard(models.TransientModel):
    _name = 'daily.attendance.print.wizard'
    _description = 'Assistant d\'impression des présences'

    def action_print_pdf(self):
        data = self.print_daily_attendance_report_data()

        if len(data['docdata']['daily_attendance_data']) == 0:
            raise UserError("Aucune donnée trouvée")
        report_action = self.env.ref('siantou_ems_core.action_report_daily_attendance')
        report_action.update({
            'name': 'Présences PDF',
        })
        return report_action.report_action(self, data=data)

    def print_daily_attendance_report_data(self, domains=None):
        domain = []

        if domains:
            for d in domains:
                domain.append(d)

        search_attendances = self.env['daily.attendance'].search(domain)

        attendances = []
        for search_attendance in search_attendances:
            attendance = {}
            attendance['employee_name'] = search_attendance.employee_id.name
            attendance['address_name'] = search_attendance.address_id.name
            attendance['attendance_type'] = ATTENDANCE_TYPE[search_attendance.attendance_type]
            attendance['punch_type'] = PUNCH_TYPE[search_attendance.punch_type]
            attendance['punching_day'] = search_attendance.punching_day
            attendance['punching_time'] = search_attendance.punching_time
            attendances.append(attendance)

        filter_title = self.env['ir.config_parameter'].sudo().get_param(f'siantou.filter_user_{self.env.user.id}', '')

        _logger.info(f'----------- tototototototo attendances {attendances} -----------')

        return {
            'docdata': {
                'title': 'Présences',
                'filter': filter_title,
                'attendance_data': attendances,
            }
        }
