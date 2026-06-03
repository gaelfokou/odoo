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
        key = list(data['docdata']['debt_data'].keys())[0]
        start_date = datetime.strftime(data['docdata']['debt_data'][key]['start_date'], DATE_FORMAT_FR)
        end_date = datetime.strftime(data['docdata']['debt_data'][key]['end_date'], DATE_FORMAT_FR)
        report_action = self.env.ref('om_hr_payroll.action_report_debt')
        report_action.update({
            'name': '{} du {}-{} PDF'.format(data['docdata']['title'], start_date, end_date),
        })
        return report_action.report_action(self, data=data)

    def sort_debt_level_rate(self, debt):
        if 'level_id' in debt:
            level = debt['level_id']
        else:
            level = 10
        if 'rate' in debt and debt['rate']:
            rate = debt['rate']
        else:
            rate = 100000.0
        return (level, rate)

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
            if not search_debt.date or not search_debt.day_of_week or not search_debt.employee_id.id:
                continue
            key = '{}'.format(search_debt.employee_id.id)
            if key not in key_debts:
                key_debts[key] = {}
                key_debts[key]['id'] = search_debt.employee_id.id
                key_debts[key]['name'] = search_debt.employee_id.name
                key_debts[key]['identifier'] = search_debt.employee_id.identifier
                key_debts[key]['data'] = []
                key_debts[key]['worked_time'] = 0.0
                key_debts[key]['amount'] = 0.0
                key_debts[key]['total_amount'] = 0.0
                key_debts[key]['reduce_amount'] = 0.0
                key_debts[key]['has_ir'] = None
                key_debts[key]['has_apecus'] = None
                key_debts[key]['has_cnps'] = None
                key_debts[key]['has_allowance_cd'] = None
                key_debts[key]['has_allowance_co'] = None
                key_debts[key]['start_date'] = search_debt.start_date
                key_debts[key]['end_date'] = search_debt.end_date
            debt = {}
            debt['id'] = search_debt.id
            debt['timetable_id'] = search_debt.timetable_id.id
            debt['date'] = search_debt.date
            debt['date_of_week'] = datetime.strftime(search_debt.date, DATE_FORMAT_FR)
            debt['class_id'] = search_debt.class_id.id
            debt['class_name'] = search_debt.class_id.name
            debt['level_id'] = search_debt.level_id.id
            debt['level_name'] = search_debt.level_id.name
            debt['subject_id'] = search_debt.subject_id.id
            debt['subject_name'] = search_debt.subject_id.name
            debt['subject_code'] = search_debt.subject_id.code
            debt['subject_shared_subject'] = '(TC)' if search_debt.subject_id.shared_subject else ''
            debt['employee_id'] = search_debt.employee_id.id
            debt['identifier'] = search_debt.employee_id.identifier
            debt['employee_name'] = search_debt.employee_id.name
            debt['start_time'] = TeacherDebtPrintWizard.convert_float_to_time(search_debt.start_time)
            debt['end_time'] = TeacherDebtPrintWizard.convert_float_to_time(search_debt.end_time)
            debt['day_of_week'] = CURRENT_WEEKDAY[search_debt.day_of_week]
            debt['worked_start_time'] = TeacherDebtPrintWizard.convert_float_to_time(search_debt.worked_start_time)
            debt['worked_end_time'] = TeacherDebtPrintWizard.convert_float_to_time(search_debt.worked_end_time)
            debt['worked_time'] = search_debt.worked_time
            debt['rate'] = search_debt.rate
            debt['amount'] = search_debt.amount
            debt['hours_credit'] = search_debt.hours_credit
            debt['total_all'] = search_debt.total_all
            debt['total_done'] = search_debt.total_done
            debt['total_awaiting'] = search_debt.total_awaiting
            if debt['total_done'] > debt['hours_credit']:
                debt['class'] = 'text-danger'
            else:
                debt['class'] = ''
            debt['status'] = STATUS_TIMETABLE[search_debt.status]
            key_debts[key]['has_ir'] = search_debt.employee_id.has_ir
            key_debts[key]['has_apecus'] = search_debt.employee_id.has_apecus
            key_debts[key]['has_cnps'] = search_debt.employee_id.has_cnps
            key_debts[key]['has_allowance_cd'] = search_debt.employee_id.has_allowance_cd
            key_debts[key]['has_allowance_co'] = search_debt.employee_id.has_allowance_co
            key_debts[key]['worked_time'] += debt['worked_time']
            key_debts[key]['amount'] += debt['amount']
            key_debts[key]['total_amount'] = key_debts[key]['amount']
            key_debts[key]['data'].append(debt)

        total_worked_time = 0.0
        total_amount = 0.0
        total_net_amount = 0.0
        total_rest_amount = 0.0
        for key in key_debts.keys():
            key_debts[key]['data'] = sorted(key_debts[key]['data'], key=self.sort_debt_level_rate)
            key_debts[key]['worked_time'] = round(key_debts[key]['worked_time'], 2)
            key_debts[key]['amount'] = round(key_debts[key]['amount'], 2)
            key_debts[key]['total_amount'] = round(key_debts[key]['total_amount'], 2)
            key_debts[key]['reduce_amount'] = round(key_debts[key]['reduce_amount'], 2)
            if key_debts[key]['amount'] < 0.0:
                key_debts[key]['amount'] = 0.0
            key_debts[key]['net_amount'] = 0.0
            key_debts[key]['net_amount'] += key_debts[key]['amount']
            key_debts[key]['rest_amount'] = 0.0
            debt_ids = self.env['teacher.debt'].search([
                ('employee_id', '=', key_debts[key]['id']),
                ('rest_amount', '>', 0.0),
            ])
            debt_ids = list(debt_ids)
            if len(debt_ids) > 0:
                for debt_id in debt_ids:
                    key_debts[key]['rest_amount'] += debt_id.rest_amount
            key_debts[key]['net_amount'] -= key_debts[key]['rest_amount']
            if key_debts[key]['net_amount'] < 0.0:
                key_debts[key]['net_amount'] = 0.0
            key_debts[key]['net_amount'] = round(key_debts[key]['net_amount'], 2)
            key_debts[key]['rest_amount'] = round(key_debts[key]['rest_amount'], 2)
            total_worked_time += key_debts[key]['worked_time']
            total_amount += key_debts[key]['amount']
            total_net_amount += key_debts[key]['net_amount']
            total_rest_amount += key_debts[key]['rest_amount']
        total_worked_time = round(total_worked_time, 2)
        total_amount = round(total_amount, 2)
        total_net_amount = round(total_net_amount, 2)
        total_rest_amount = round(total_rest_amount, 2)

        key_debts = sorted(key_debts.items(), key=self.sort_debt)

        key_debts = dict(key_debts)

        _logger.info(f'----------- tototototototo key_debts {key_debts} -----------')

        filter_title = self.env['ir.config_parameter'].sudo().get_param(f'siantou.filter_user_{self.env.user.id}', '')

        title = 'Émargements des enseignants vacataires'

        return {
            'docdata': {
                'title': title,
                'filter': filter_title,
                'debt_data': key_debts,
                'total_worked_time': total_worked_time,
                'total_amount': total_amount,
                'total_net_amount': total_net_amount,
                'total_rest_amount': total_rest_amount,
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

    @staticmethod
    def convert_time_to_float(tm):
        tm = str(tm)
        tm = tm.split(':')
        tm = tm[0:2]
        tm = '.'.join(tm)
        tm = eval(tm)
        tm = float(tm)
        tm = round(tm, 2)
        return tm

    @staticmethod
    def increment_float_time(tm, n=0.0):
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
        tm = time(int(tm[0]), int(tm[1]))
        n = str(n)
        n = n.split('.')
        if len(n) == 1:
            n.append('0')
        if len(n[0]) == 1:
            n[0] = '0{}'.format(n[0])
        elif len(n[0]) > 2:
            n[0] = '{}'.format(n[0][0:2])
        if int(n[0]) > 23:
            n[0] = '00'
        if len(n[1]) == 1:
            n[1] = '{}0'.format(n[1])
        elif len(n[1]) > 2:
            n[1] = '{}'.format(n[1][0:2])
        if int(n[1]) > 59:
            n[1] = '00'
        tm = datetime.combine(date.min, tm) + timedelta(hours=int(n[0]), minutes=int(n[1]))
        tm = datetime.strftime(tm, TIME_FORMAT_FR)
        tm = TeacherDebtPrintWizard.convert_time_to_float(tm)
        return tm

    @staticmethod
    def paginate_calendar(items, page_size=10, page_number=1):
        if page_size == 0:
            page_size = 10
        keys = range(len(items.keys()))
        keys = list(keys)
        pages_total = [keys[i:i+page_size] for i in range(0, len(keys), page_size)]
        start_index = (page_number - 1) * page_size
        end_index = start_index + page_size
        pages = keys[start_index:end_index]
        data = {}
        for i, key in enumerate(items.keys()):
            if i in pages:
                data[key] = items[key]
        pages = data
        return {
            'total': len(items.keys()),
            'pages_total': len(pages_total),
            'pages': pages,
        }

    @staticmethod
    def is_float(data):
        try:
            float(data)
            return True
        except ValueError:
            return False

    @staticmethod
    def format_timetable(data, hours=[]):
        n = 0.0
        current_data = []
        current_hours = []
        timetables = {}
        df = {}

        for i in range(len(data)):
            data[i]['start_time'] = round(data[i]['start_time'], 2)
            data[i]['end_time'] = round(data[i]['end_time'], 2)

        if len(hours) > 0:
            for i in range(len(data)):
                for hour in hours:
                    if not (TeacherDebtPrintWizard.increment_float_time(data[i]['start_time']) <= TeacherDebtPrintWizard.increment_float_time(hour[0]) and TeacherDebtPrintWizard.increment_float_time(data[i]['end_time']) > TeacherDebtPrintWizard.increment_float_time(hour[0])) or not (TeacherDebtPrintWizard.increment_float_time(data[i]['start_time']) < TeacherDebtPrintWizard.increment_float_time(hour[1]) and TeacherDebtPrintWizard.increment_float_time(data[i]['end_time']) >= TeacherDebtPrintWizard.increment_float_time(hour[1])):
                        current_data.append(data[i])
                        break
                    else:
                        if not (TeacherDebtPrintWizard.increment_float_time(data[i]['start_time']) == TeacherDebtPrintWizard.increment_float_time(hour[0]) and TeacherDebtPrintWizard.increment_float_time(data[i]['end_time']) == TeacherDebtPrintWizard.increment_float_time(hour[1])):
                            if not (TeacherDebtPrintWizard.increment_float_time(data[i]['start_time']) < TeacherDebtPrintWizard.increment_float_time(hour[0]) and TeacherDebtPrintWizard.increment_float_time(data[i]['end_time']) > TeacherDebtPrintWizard.increment_float_time(hour[1])):
                                if TeacherDebtPrintWizard.increment_float_time(data[i]['start_time']) == TeacherDebtPrintWizard.increment_float_time(hour[0]):
                                    data[i]['start_time'] = hour[1]
                                    current_data.append(data[i])
                                    break
                                else:
                                    if TeacherDebtPrintWizard.increment_float_time(data[i]['end_time']) == TeacherDebtPrintWizard.increment_float_time(hour[1]):
                                        data[i]['end_time'] = hour[0]
                                        current_data.append(data[i])
                                        break
                            else:
                                data1 = copy.deepcopy(data[i])
                                data2 = copy.deepcopy(data[i])
                                data1['end_time'] = hour[0]
                                data2['start_time'] = hour[1]
                                current_data.append(data1)
                                current_data.append(data2)
                                break
            data = current_data

        data.sort(key=lambda d: d['date'])
        sorted_data = copy.deepcopy(data)

        for d in data:
            hours.append([d['start_time'], d['end_time']])

        for i, hour in enumerate(hours):
            if i == 0:
                n = hour[1] - hour[0]
            else:
                if n > hour[1] - hour[0]:
                    n = hour[1] - hour[0]

        n = round(n, 2)

        hours.sort(key=lambda h: h[0])

        for i in range(len(hours)):
            while TeacherDebtPrintWizard.increment_float_time(hours[i][0]) < TeacherDebtPrintWizard.increment_float_time(hours[i][1]):
                if TeacherDebtPrintWizard.increment_float_time(hours[i][0], n) == 0.0:
                    h = '{}-{}'.format(TeacherDebtPrintWizard.increment_float_time(hours[i][0]), TeacherDebtPrintWizard.increment_float_time(hours[i][1]))
                    current_hours.append(h)
                    hours[i][0] = TeacherDebtPrintWizard.increment_float_time(hours[i][1])
                else:
                    if TeacherDebtPrintWizard.increment_float_time(hours[i][0], n) < TeacherDebtPrintWizard.increment_float_time(hours[i][1]):
                        h = '{}-{}'.format(TeacherDebtPrintWizard.increment_float_time(hours[i][0]), TeacherDebtPrintWizard.increment_float_time(hours[i][0], n))
                        current_hours.append(h)
                        hours[i][0] = TeacherDebtPrintWizard.increment_float_time(hours[i][0], n)
                    else:
                        h = '{}-{}'.format(TeacherDebtPrintWizard.increment_float_time(hours[i][0]), TeacherDebtPrintWizard.increment_float_time(hours[i][1]))
                        current_hours.append(h)
                        hours[i][0] = TeacherDebtPrintWizard.increment_float_time(hours[i][1])

        current_hours = list(set(current_hours))
        current_hours.sort(key=lambda h: float(h.split('-')[0]))

        for d in sorted_data:
            if d['date'].weekday() == 0:
                monday = d['date']
            else:
                monday = d['date'] - timedelta(days=d['date'].weekday())
            monday = datetime.strftime(monday, DATE_FORMAT)
            if monday not in timetables:
                timetables[monday] = {
                    'Heure': [hour for hour in current_hours],
                    'Lundi': [],
                    'Mardi': [],
                    'Mercredi': [],
                    'Jeudi': [],
                    'Vendredi': [],
                    'Samedi': [],
                    'Dimanche': [],
                }

                for i in range(len(timetables[monday]['Heure'])):
                    for key in timetables[monday].keys():
                        if key == 'Heure':
                            continue
                        timetables[monday][key].append(np.nan)
            if monday not in df:
                df[monday] = pd.DataFrame(timetables[monday], dtype=str)
            while TeacherDebtPrintWizard.increment_float_time(d['start_time']) < TeacherDebtPrintWizard.increment_float_time(d['end_time']):
                if TeacherDebtPrintWizard.increment_float_time(d['start_time'], n) == 0.0:
                    h = '{}-{}'.format(TeacherDebtPrintWizard.increment_float_time(d['start_time']), TeacherDebtPrintWizard.increment_float_time(d['end_time']))
                    for i, row in df[monday].iterrows():
                        if h == timetables[monday]['Heure'][i]:
                            for j, column in enumerate(df[monday].columns):
                                for k, key in enumerate(timetables[monday].keys()):
                                    if k == d['date'].weekday() + 1:
                                        if column == key:
                                            if TeacherDebtPrintWizard.is_float(str(df[monday].loc[i, column])) and np.isnan(float(str(df[monday].loc[i, column]))):
                                                df[monday].loc[i, column] = str(d['id'])
                                            else:
                                                df[monday].loc[i, column] = '{}-{}'.format(df[monday].loc[i, column], str(d['id']))
                                        break
                    d['start_time'] = TeacherDebtPrintWizard.increment_float_time(d['end_time'])
                else:
                    if TeacherDebtPrintWizard.increment_float_time(d['start_time'], n) < TeacherDebtPrintWizard.increment_float_time(d['end_time']):
                        h = '{}-{}'.format(TeacherDebtPrintWizard.increment_float_time(d['start_time']), TeacherDebtPrintWizard.increment_float_time(d['start_time'], n))
                        for i, row in df[monday].iterrows():
                            if h == timetables[monday]['Heure'][i]:
                                for j, column in enumerate(df[monday].columns):
                                    for k, key in enumerate(timetables[monday].keys()):
                                        if k == d['date'].weekday() + 1:
                                            if column == key:
                                                if TeacherDebtPrintWizard.is_float(str(df[monday].loc[i, column])) and np.isnan(float(str(df[monday].loc[i, column]))):
                                                    df[monday].loc[i, column] = str(d['id'])
                                                else:
                                                    df[monday].loc[i, column] = '{}-{}'.format(df[monday].loc[i, column], str(d['id']))
                                            break
                        d['start_time'] = TeacherDebtPrintWizard.increment_float_time(d['start_time'], n)
                    else:
                        h = '{}-{}'.format(TeacherDebtPrintWizard.increment_float_time(d['start_time']), TeacherDebtPrintWizard.increment_float_time(d['end_time']))
                        for i, row in df[monday].iterrows():
                            if h == timetables[monday]['Heure'][i]:
                                for j, column in enumerate(df[monday].columns):
                                    for k, key in enumerate(timetables[monday].keys()):
                                        if k == d['date'].weekday() + 1:
                                            if column == key:
                                                if TeacherDebtPrintWizard.is_float(str(df[monday].loc[i, column])) and np.isnan(float(str(df[monday].loc[i, column]))):
                                                    df[monday].loc[i, column] = str(d['id'])
                                                else:
                                                    df[monday].loc[i, column] = '{}-{}'.format(df[monday].loc[i, column], str(d['id']))
                                            break
                        d['start_time'] = TeacherDebtPrintWizard.increment_float_time(d['end_time'])

        for monday in df.keys():
            df[monday].replace(np.nan, '-', inplace=True)

            for key in timetables[monday].keys():
                timetables[monday][key] = list(df[monday][key])
                if key != 'Heure':
                    for i, vals in enumerate(timetables[monday][key]):
                        timetables[monday][key][i] = []
                        if vals != '-':
                            for v in vals.split('-'):
                                timetables[monday][key][i].append([d for d in data if d['id'] == int(v)][0])

            monday = datetime.strptime(f"{monday}", DATE_FORMAT).date()
            saturday = monday + timedelta(days=5)
            monday_fr = datetime.strftime(monday, DATE_FORMAT_FR)
            saturday_fr = datetime.strftime(saturday, DATE_FORMAT_FR)
            monday = datetime.strftime(monday, DATE_FORMAT)
            saturday = '{} - {}'.format(monday_fr, saturday_fr)
            timetables[saturday] = timetables[monday]
            del(timetables[monday])

        _logger.info(f'----------- tototototototo timetables {timetables} -----------')

        return timetables

    def convert_number_to_weekday(self, number):
        if number == '0':
            return "Lundi"
        elif number == '1':
            return "Mardi"
        elif number == '2':
            return "Mercredi"
        elif number == '3':
            return "Jeudi"
        elif number == '4':
            return "Vendredi"
        elif number == '5':
            return "Samedi"
        elif number == '6':
            return "Dimanche"

    def format_time(self, input_str):
        """
        Prend une chaîne d'entrée, vérifie si elle contient ',' ou '.',
        fait un split, ajoute des zéros si nécessaire, et retourne les deux
        parties jointes par ':'.

        :param input_str: La chaîne d'entrée (str)
        :return: Une chaîne formatée (str)
        """

        input_str = str(input_str)

        if ',' in input_str:
            parts = input_str.split(',')
        elif '.' in input_str:
            parts = input_str.split('.')
        else:
            raise ValueError("La chaîne d'entrée doit contenir ',' ou '.'")

        # Prendre la première et la deuxième valeur
        first_part = parts[0].strip()
        second_part = parts[1].strip() if len(parts) > 1 else '0'

        # Ajouter 0 devant ou après si nécessaire
        first_part = first_part.zfill(2)  # Ajoute un 0 devant si le chiffre est unique
        second_part = second_part.ljust(2, '0')  # Ajoute un 0 après si le chiffre est unique

        # Joindre avec ':'
        return f"{first_part}:{second_part}"
