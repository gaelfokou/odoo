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

_logger = logging.getLogger(__name__)


class StudentPrintWizard(models.TransientModel):
    _name = 'student.print.wizard'
    _description = 'Assistant d\'impression des étudiants'

    def action_print_pdf(self):
        data = self.print_student_report_data()

        if len(data['docdata']['student_data']) == 0:
            raise UserError("Aucune donnée trouvée")
        report_action = self.env.ref('siantou_ems_core.action_report_student')
        report_action.update({
            'name': 'Étudiants PDF',
        })
        return report_action.report_action(self, data=data)

    def sort_student(self, student):
        name = student['name'] if student['name'] else ''
        name = name.strip()
        name = name.lower()
        return name

    def print_student_report_data(self, domains=None):
        domain = []

        if domains:
            for d in domains:
                domain.append(d)

        search_students = self.env['oe.school.student'].search(domain)

        students = []
        for search_student in search_students:
            student = {}
            student['name'] = search_student.name
            student['last_name'] = search_student.last_name
            student['first_name'] = search_student.first_name
            student['email'] = search_student.email
            student['private_phone'] = search_student.private_phone
            student['matricule'] = search_student.matricule
            students.append(student)

        students = sorted(students, key=self.sort_student)

        filter_title = self.env['ir.config_parameter'].sudo().get_param(f'siantou.filter_user_{self.env.user.id}', '')

        _logger.info(f'----------- tototototototo students {students} -----------')

        return {
            'docdata': {
                'title': 'Étudiants',
                'filter': filter_title,
                'student_data': students,
            }
        }
