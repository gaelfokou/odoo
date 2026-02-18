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

class SubjectPrintWizard(models.TransientModel):
    _name = 'subject.print.wizard'
    _description = 'Assistant d\'impression des subjects'

    def action_print_pdf(self):
        data = self.print_subject_report_data()

        # Appeler le rapport PDF
        if len(data['docdata']['subject_data']) == 0:
            raise UserError("Aucune donnée trouvée")
        report_action = self.env.ref('siantou_ems_core.action_report_subject')
        return report_action.report_action(self, data=data)

    def sort_subject(self, subject):
        name = subject['name'] if subject['name'] else ''
        name = name.strip()
        name = name.lower()
        return name

    def print_subject_report_data(self, domains=None):
        # Récupérer les emplois du temps pour le semestre sélectionné
        domain = []

        if domains:
            for d in domains:
                domain.append(d)

        search_subjects = self.env['siantou.ems.core.subject'].search(domain)

        total_hours_credit = 0.0
        subjects = []
        for search_subject in search_subjects:
            subject = {}
            subject['code'] = search_subject.code
            subject['name'] = search_subject.name
            subject['shared_subject'] = 'Oui' if search_subject.shared_subject else 'Non'
            subject['hours_credit'] = search_subject.hours_credit
            ue_ids = [ue_id.name for ue_id in search_subject.ue_ids]
            subject['ue_ids'] = ' / '.join(ue_ids)
            total_hours_credit += subject['hours_credit']
            subjects.append(subject)

        subjects = sorted(subjects, key=self.sort_subject)

        filter_title = self.env['ir.config_parameter'].sudo().get_param(f'siantou.filter_user_{self.env.user.id}', '')

        _logger.info(f'----------- tototototototo subjects {subjects} -----------')

        return {
            'docdata': {
                'title': 'Cours',
                'filter': filter_title,
                'subject_data': subjects,
                'total_hours_credit': total_hours_credit,
            }
        }
