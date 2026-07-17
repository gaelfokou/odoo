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

TYPE_COUR = {
    'cj': 'Cours du jour',
    'cs': 'Cours du soir',
}

_logger = logging.getLogger(__name__)

class ClassPrintWizard(models.TransientModel):
    _name = 'class.print.wizard'
    _description = 'Assistant d\'impression des classes'

    def action_print_pdf(self):
        data = self.print_class_report_data()

        if len(data['docdata']['class_data']) == 0:
            raise UserError("Aucune donnée trouvée")
        report_action = self.env.ref('siantou_ems_core.action_report_class')
        report_action.update({
            'name': 'Classes PDF',
        })
        return report_action.report_action(self, data=data)

    def sort_classe(self, classe):
        name = classe['name'] if classe['name'] else ''
        name = name.strip()
        name = name.lower()
        return name

    def print_class_report_data(self, domains=None):
        domain = []

        if domains:
            for d in domains:
                domain.append(d)

        search_classes = self.env['siantou.ems.core.class'].search(domain)

        classes = []
        for search_classe in search_classes:
            classe = {}
            classe['name'] = search_classe.name
            classe['school'] = search_classe.school_id.name
            classe['cycle'] = search_classe.cycle_id.name
            classe['department'] = search_classe.department_id.name
            classe['field_of_study'] = search_classe.field_of_study_id.name
            classe['level'] = search_classe.level_id.name
            classe['specialty'] = search_classe.specialty_id.name
            classe['option'] = search_classe.option_id.name
            classe['number_of_student'] = search_classe.number_of_student
            classe['type_cour'] = TYPE_COUR[search_classe.type_cour]
            classes.append(classe)

        classes = sorted(classes, key=self.sort_classe)

        filter_title = self.env['ir.config_parameter'].sudo().get_param(f'siantou.filter_user_{self.env.user.id}', '')

        _logger.info(f'----------- tototototototo classes {classes} -----------')

        return {
            'docdata': {
                'title': 'Classes',
                'filter': filter_title,
                'class_data': classes,
            }
        }

    def print_class_subject_report_data(self, domains=None):
        domain = []

        if domains:
            for d in domains:
                domain.append(d)

        search_classes = self.env['siantou.ems.core.class'].search(domain)

        subjects = []
        for search_classe in search_classes:
            for ue_id in search_classe.ue_ids:
                semester_ids = ue_id.semester_ids.filtered(lambda rec: rec.year_id.id == search_classe.year_id.id)
                for semester_id in semester_ids:
                    subject_ids = ue_id.subject_ids.filtered(lambda rec: rec.ue_ids.ids == semester_id.ue_ids.ids)
                    for subject_id in subject_ids:
                        subject = {}
                        subject['id'] = subject_id.id
                        subject['code'] = subject_id.code
                        subject['name'] = subject_id.name
                        subject['ue_id'] = ue_id.id
                        subject['ue_code'] = ue_id.code
                        subject['ue_name'] = ue_id.name
                        subject['hours_credit'] = subject_id.hours_credit
                        subject['total_credit'] = subject_id.total_credit
                        subject['semester_id'] = semester_id.id
                        subject['semester_name'] = semester_id.name
                        subject['class_id'] = search_classe.id
                        subject['class_name'] = search_classe.name
                        subjects.append(subject)

        subjects = sorted(subjects, key=self.sort_classe)

        filter_title = self.env['ir.config_parameter'].sudo().get_param(f'siantou.filter_user_{self.env.user.id}', '')

        _logger.info(f'----------- tototototototo subjects {subjects} -----------')

        return {
            'docdata': {
                'title': 'Cours',
                'filter': filter_title,
                'subject_data': subjects,
            }
        }
