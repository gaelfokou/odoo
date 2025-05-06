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

        search_classes = self.env['oe.school.class'].search(domain)

        classes = []
        for search_classe in search_classes:
            classe = {}
            classe['id'] = search_classe.id
            classe['name'] = search_classe.name
            classe['last_name'] = search_classe.last_name
            classe['first_name'] = search_classe.first_name
            classe['email'] = search_classe.email
            classe['date_naissance'] = search_classe.date_naissance
            classe['matricule'] = search_classe.matricule
            classes.append(classe)

        title = self.env['ir.config_parameter'].get_param(f'filter.{self.env.user.id}', '')

        _logger.info(f'----------- tototototototo classes {classes} -----------')

        return {
            'docdata': {
                'filter': title,
                'classe_data': classes,
            }
        }
