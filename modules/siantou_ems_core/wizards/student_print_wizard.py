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

_logger = logging.getLogger(__name__)

class TeacherPrintWizard(models.TransientModel):
    _name = 'student.print.wizard'
    _description = 'Assistant d\'impression des étudiants'

    def print_student(self):
        data = self.print_student_report_data()

        # Appeler le rapport PDF
        if not data['docdata']['student_data']:
            raise UserError("Aucune donnée trouvée")
        report_action = self.env.ref('siantou_ems_core.action_report_student')
        return report_action.report_action(self, data=data)

    def print_student_report_data(self, domains=None):
        # Récupérer les emplois du temps pour le semestre sélectionné
        domain = []

        if domains:
            for d in domains:
                domain.append(d)

        search_students = self.env['oe.school.student'].search(domain)

        students = []
        for search_student in search_students:
            student = {}
            student['id'] = search_student.id
            student['name'] = search_student.name
            student['last_name'] = search_student.last_name
            student['first_name'] = search_student.first_name
            student['email'] = search_student.email
            student['date_naissance'] = search_student.date_naissance
            student['matricule'] = search_student.matricule
            students.append(student)

        title = self.env['ir.config_parameter'].get_param(f'filter.{self.env.user.id}', '')

        _logger.info(f'----------- tototototototo students {students} -----------')

        return {
            'docdata': {
                'filter': title,
                'student_data': students,
            }
        }
