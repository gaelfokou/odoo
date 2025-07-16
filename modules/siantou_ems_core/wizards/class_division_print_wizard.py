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

    def print_class(self):
        data = self.print_class_report_data()

        # Appeler le rapport PDF
        if not data['docdata']['class_data']:
            raise UserError("Aucune donnée trouvée")
        report_action = self.env.ref('siantou_ems_core.action_report_class')
        return report_action.report_action(self, data=data)

    def print_class_report_data(self, domains=None):
        # Récupérer les emplois du temps pour le semestre sélectionné
        domain = []

        if domains:
            for d in domains:
                domain.append(d)

        search_classes = self.env['siantou.ems.core.class'].search(domain)

        classes = []
        for search_classe in search_classes:
            classe = {}
            classe['name'] = search_classe.name
            classe['year'] = search_classe.year_id.name
            classe['school'] = search_classe.school_id.name
            classe['field_of_study'] = search_classe.field_of_study_id.name
            classe['level'] = search_classe.level_id.name
            classe['specialty'] = search_classe.specialty_id.name
            classe['option'] = search_classe.option_id.name
            classe['type_cour'] = TYPE_COUR[search_classe.type_cour]
            classes.append(classe)

        title = self.env['ir.config_parameter'].sudo().get_param(f'siantou.filter_user_{self.env.user.id}', '')

        _logger.info(f'----------- tototototototo classes {classes} -----------')

        return {
            'docdata': {
                'filter': title,
                'class_data': classes,
            }
        }
