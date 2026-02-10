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

DATE_FORMAT = '%Y-%m-%d'
DATE_FORMAT_FR = '%d/%m/%Y'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATETIME_FORMAT_FR = '%d/%m/%Y %H:%M'
TIME_FORMAT = '%H:%M:%S'
TIME_FORMAT_FR = '%H:%M'

CURRENT_WEEKDAY = {
    '0': 'Lundi',
    '1': 'Mardi',
    '2': 'Mercredi',
    '3': 'Jeudi',
    '4': 'Vendredi',
    '5': 'Samedi',
    '6': 'Dimanche'
}

TYPE_COUR = {
    'cj': 'Cours du jour',
    'cs': 'Cours du soir',
}

_logger = logging.getLogger(__name__)

class ProgressReportPrintWizard(models.TransientModel):
    _name = 'progress.report.print.wizard'
    _description = 'Assistant d\'impression des fiches de progression'

    def action_print_pdf(self):
        data = self.print_progress_report_data()

        # Appeler le rapport PDF
        if len(data['docdata']['report_data']) == 0:
            raise UserError("Aucune donnée trouvée")
        report_action = self.env.ref('siantou_ems_core.action_report_progress_report')
        report_action.update({
            'name': 'Fiches de progression PDF',
        })
        return report_action.report_action(self, data=data)

    def print_progress_report_data(self, domains=None):
        # Récupérer les emplois du temps pour le semestre sélectionné
        domain = []

        if domains:
            for d in domains:
                domain.append(d)

        search_reports = self.env['siantou.ems.core.progress.report'].search(domain)

        reports = []
        for search_report in search_reports:
            report = {}
            report['id'] = search_report.id
            report['name'] = search_report.name
            report['classe'] = search_report.class_id.name
            report['subject'] = search_report.subject_id.name
            session_ids = search_report.session_ids
            session_ids = list(session_ids)
            sessions = []
            for session_id in session_ids:
                session = {}
                session['id'] = session_id.id
                session['name'] = session_id.name
                session['description'] = session_id.description
                session['date'] = datetime.strftime(session_id.timetable_id.date, DATE_FORMAT_FR)
                session['start_time'] = ProgressReportPrintWizard.convert_float_to_time(session_id.timetable_id.start_time)
                session['end_time'] = ProgressReportPrintWizard.convert_float_to_time(session_id.timetable_id.end_time)
                sessions.append(session)
            sessions = sorted(sessions, key=lambda item: int(item['name'].replace('Séance ', '')))
            report['sessions'] = sessions
            reports.append(report)

        filter_title = self.env['ir.config_parameter'].sudo().get_param(f'siantou.filter_user_{self.env.user.id}', '')

        _logger.info(f'----------- tototototototo reports {reports} -----------')

        return {
            'docdata': {
                'title': 'Fiches de progression',
                'filter': filter_title,
                'report_data': reports,
            }
        }

    @staticmethod
    def convert_float_to_time(tm, has_second=False):
        tm = str(tm)
        tm = tm.split('.')
        if len(tm) == 1:
            tm.append('0')
        if len(tm[0]) == 1:
            tm[0] = '0{}'.format(tm[0])
        elif len(tm[0]) > 2:
            tm[0] = '{}'.format(tm[0][0:2])
        if int(tm[0]) > 23:
            tm[0] = '00'
        if len(tm[1]) == 1:
            tm[1] = '{}0'.format(tm[1])
        elif len(tm[1]) > 2:
            tm[1] = '{}'.format(tm[1][0:2])
        if int(tm[1]) > 59:
            tm[1] = '00'
        tm = ':'.join(tm)
        if has_second:
            tm = '{}:00'.format(tm)
        return tm
