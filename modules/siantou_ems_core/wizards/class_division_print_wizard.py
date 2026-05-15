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
