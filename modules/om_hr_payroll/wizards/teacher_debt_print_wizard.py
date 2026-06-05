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
    '6': 'Dimanche',
}

STATUS_TIMETABLE = {
    'pending': 'En attente',
    'progress': 'En cours',
    'present': 'Présent',
    'absent': 'Absent',
    'permission': 'Permission',
    'exception': 'Exception',
    'delay': 'Retard',
}

_logger = logging.getLogger(__name__)

class TeacherDebtPrintWizard(models.TransientModel):
    _name = 'teacher.debt.print.wizard'
    _description = 'Assistant d\'impression des émargements des enseignants'

    def action_print_pdf(self):
        data = self.print_debt_report_data()

        if len(data['docdata']['debt_data'].keys()) == 0:
            raise UserError("Aucune donnée trouvée")
        report_action = self.env.ref('om_hr_payroll.action_report_debt')
        report_action.update({
            'name': '{} PDF'.format(data['docdata']['title']),
        })
        return report_action.report_action(self, data=data)

    def sort_debt_date(self, debt):
        if 'start_date' in debt:
            start_date = debt['start_date']
        else:
            start_date = datetime.strptime('2015-12-15', DATE_FORMAT).date()
        return start_date

    def sort_debt(self, debt):
        name = debt[1]['name'] if debt[1]['name'] else ''
        name = name.strip()
        name = name.lower()
        return name

    def print_debt_report_data(self, domains=None):
        domain = []

        if domains:
            for d in domains:
                domain.append(d)

        search_debts = self.env['teacher.debt'].search(domain)

        key_debts = {}
        for search_debt in search_debts:
            key = '{}'.format(search_debt.employee_id.id)
            if key not in key_debts:
                key_debts[key] = {}
                key_debts[key]['id'] = search_debt.employee_id.id
                key_debts[key]['name'] = search_debt.employee_id.name
                key_debts[key]['identifier'] = search_debt.employee_id.identifier
                key_debts[key]['data'] = []
                key_debts[key]['amount'] = 0.0
                key_debts[key]['rest_amount'] = 0.0
                key_debts[key]['total_amount'] = 0.0
                key_debts[key]['total_rest_amount'] = 0.0
            debt = {}
            debt['id'] = search_debt.id
            debt['name'] = search_debt.name
            debt['description'] = search_debt.description
            debt['start_date'] = search_debt.start_date
            debt['start_date_of_week'] = datetime.strftime(search_debt.start_date, DATE_FORMAT_FR)
            debt['end_date'] = search_debt.end_date
            debt['end_date_of_week'] = datetime.strftime(search_debt.end_date, DATE_FORMAT_FR)
            debt['employee_id'] = search_debt.employee_id.id
            debt['identifier'] = search_debt.employee_id.identifier
            debt['employee_name'] = search_debt.employee_id.name
            debt['amount'] = search_debt.amount
            debt['rest_amount'] = search_debt.rest_amount
            payment_ids = search_debt.payment_ids
            payment_ids = list(payment_ids)
            payments = []
            for payment_id in payment_ids:
                payment = {}
                payment['id'] = payment_id.id
                payment['name'] = payment_id.name
                payment['date'] = payment_id.date
                payment['date_of_week'] = datetime.strftime(payment_id.date, DATE_FORMAT_FR)
                payment['amount'] = payment_id.amount
                payments.append(payment)
            debt['payments'] = payments
            key_debts[key]['amount'] += debt['amount']
            key_debts[key]['rest_amount'] += debt['rest_amount']
            key_debts[key]['total_amount'] = key_debts[key]['amount']
            key_debts[key]['total_rest_amount'] = key_debts[key]['rest_amount']
            key_debts[key]['data'].append(debt)

        total_amount = 0.0
        total_rest_amount = 0.0
        for key in key_debts.keys():
            key_debts[key]['data'] = sorted(key_debts[key]['data'], key=self.sort_debt_date)
            total_amount += key_debts[key]['amount']
            total_rest_amount += key_debts[key]['rest_amount']
        total_amount = round(total_amount, 2)
        total_rest_amount = round(total_rest_amount, 2)

        key_debts = sorted(key_debts.items(), key=self.sort_debt)

        key_debts = dict(key_debts)

        _logger.info(f'----------- tototototototo key_debts {key_debts} -----------')

        filter_title = None

        title = 'Dettes des enseignants'

        return {
            'docdata': {
                'title': title,
                'filter': filter_title,
                'debt_data': key_debts,
                'total_amount': total_amount,
                'total_rest_amount': total_rest_amount,
            }
        }
