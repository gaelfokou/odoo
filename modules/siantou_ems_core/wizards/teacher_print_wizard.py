import logging

from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from pprint import pformat
import pandas as pd
import numpy as np
import re
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import copy

DATE_FORMAT = '%Y-%m-%d'
DATE_FORMAT_FR = '%d/%m/%Y'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATETIME_FORMAT_FR = '%d/%m/%Y %H:%M'
TIME_FORMAT = '%H:%M'

CURRENT_WEEKDAY = {
    0: 'Lundi',
    1: 'Mardi',
    2: 'Mercredi',
    3: 'Jeudi',
    4: 'Vendredi',
    5: 'Samedi',
    6: 'Dimanche',
}

STATUS_TIMETABLE = {
    '0': 'En attente',
    '1': 'Présent',
    '2': 'Absent',
    '3': 'Permissionnaire',
    '4': 'Exception',
}

_logger = logging.getLogger(__name__)

class TeacherPrintWizard(models.TransientModel):
    _name = 'teacher.print.wizard'
    _description = 'Assistant d\'impression des enseignants'

    is_teacher = fields.Boolean(
        'Est un enseignant',
        default=True,
    )

    is_permanent = fields.Boolean(
        'Est un permanent',
        default=False,
    )

    def print_teacher(self):
        data = self.print_teacher_report_data()

        # Appeler le rapport PDF
        if not data['docdata']['teacher_data']:
            raise UserError("Aucune donnée trouvée")
        report_action = self.env.ref('siantou_ems_core.action_report_teacher')
        return report_action.report_action(self, data=data)

    def print_teacher_report_data(self, domains=None):
        # Récupérer les emplois du temps pour le semestre sélectionné
        domain = []

        domain.append(('is_teacher', '=', self.is_teacher))

        domain.append(('is_permanent', '=', self.is_permanent))

        if domains:
            for d in domains:
                domain.append(d)

        search_teachers = self.env['hr.employee'].search(domain)

        teachers = []
        for search_teacher in search_teachers:
            teacher = {}
            teacher['id'] = search_teacher.id
            teacher['name'] = search_teacher.name
            teacher['last_name'] = search_teacher.last_name
            teacher['first_name'] = search_teacher.first_name
            teacher['work_email'] = search_teacher.work_email
            teacher['birthday'] = search_teacher.birthday
            teacher['is_teacher'] = search_teacher.is_teacher
            teacher['is_permanent'] = search_teacher.is_permanent
            teacher['identifier'] = search_teacher.identifier
            teacher['weekly_hours_limit'] = search_teacher.weekly_hours_limit
            teachers.append(teacher)

        title = self.env['ir.config_parameter'].get_param(f'hr.employee.filter.{self.env.user.id}', '')
        self.env['ir.config_parameter'].set_param(f'hr.employee.filter.{self.env.user.id}', '')

        _logger.info(f'----------- tototototototo teachers {teachers} -----------')

        return {
            'docdata': {
                'filter': title,
                'teacher_data': teachers,
            }
        }
