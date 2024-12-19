# helpers.py
from odoo import http
from odoo.addons.portal.controllers import portal
from odoo.exceptions import UserError, ValidationError
import pandas as pd
import numpy as np
import re
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import logging

DATE_FORMAT = '%Y-%m-%d'
DATE_FORMAT_FR = '%d/%m/%Y'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATETIME_FORMAT_FR = '%d/%m/%Y %H:%M:%S'
TIME_FORMAT = '%H:%M'

CURRENT_HOUR = [
    '8.0-10.0',
    '10.0-12.0',
    '12.0-13.0',
    '13.0-15.0',
    '15.0-17.0',
]

_logger = logging.getLogger(__name__)

class Helpers:
    @staticmethod
    def timetable(search='', search_in='all'):
        searchbar_inputs = {
            'all': {'label': 'Tout', 'input': 'all', 'domain': []},
            'filiere': {'label': 'Filière', 'input': 'filiere', 'domain': [('field_of_study_id.name', 'like', search)]},
            'cours': {'label': 'Cours', 'input': 'cours', 'domain': [('subject_id.name', 'like', search)]},
            'enseignant': {'label': 'Enseignant', 'input': 'enseignant', 'domain': [('employee_id.name', 'like', search)]},
            'filiere': {'label': 'Filière', 'input': 'filiere', 'domain': [('field_of_study_id.name', 'like', search)]},
            'niveau': {'label': 'Niveau', 'input': 'niveau', 'domain': [('level_id.name', 'like', search)]},
            'cycle': {'label': 'Cycle', 'input': 'cycle', 'domain': [('cycle_id.name', 'like', search)]},
        }
        if search_in not in searchbar_inputs.keys():
            search_in = 'all'
        search_domain = searchbar_inputs[search_in]['domain']

        order = 'date asc'

        search_timetables = []
        if http.request.env.user.employee_id.id:
            user = http.request.env.user.employee_id
            search_domain.append(('employee_id', '=', user.id))

            timetables = http.request.env['siantou.ems.timetable.timetable'].sudo().search(search_domain, order=order)
            timetables = list(timetables)
            search_timetables = timetables
        else:
            user = http.request.env.user
            # Chercher l'étudiant en fonction de l'ID de l'utilisateur (user_id)
            student = http.request.env['oe.school.student'].sudo().search([('user_id', '=', user.id)], limit=1)
            if student:
                # Si l'étudiant est trouvé, on filtre par cycle, niveau et filière
                search_domain.append(('level_id', '=', student.level_id.id))
                search_domain.append(('field_of_study_id', '=', student.field_of_study_id.id))

                timetables = http.request.env['siantou.ems.timetable.timetable'].sudo().search(search_domain, order=order)
                timetables = list(timetables)
                search_timetables = timetables

        _logger.info(f'----------- tototototototo search_timetables {search_timetables} -----------')

        return search_timetables, searchbar_inputs

    @staticmethod
    def schoolfee(search='', search_in='all'):
        searchbar_inputs = {
            'all': {'label': 'Tout', 'input': 'all', 'domain': []},
        }
        if search_in not in searchbar_inputs.keys():
            search_in = 'all'
        search_domain = searchbar_inputs[search_in]['domain']

        order = 'date_payment asc'

        user = http.request.env.user
        # Chercher l'étudiant en fonction de l'ID de l'utilisateur (user_id)
        student = http.request.env['oe.school.student'].sudo().search([('user_id', '=', user.id)], limit=1)
        search_schoolfees = []
        if student:
            # Si l'étudiant est trouvé, on filtre par cycle, niveau et filière
            search_domain.append(('student_id', '=', student.id))

            schoolfees = http.request.env['education.fee.payment'].sudo().search(search_domain, order=order)
            schoolfees = list(schoolfees)
            search_schoolfees = schoolfees

            search_domain = []
            search_domain.append(('student_id', '=', student.student_enroll_id.id))

            schoolfees = http.request.env['education.fee.payment.enrollment'].sudo().search(search_domain, order=order)
            schoolfees = list(schoolfees)
            search_schoolfees += schoolfees

        _logger.info(f'----------- tototototototo search_schoolfees {search_schoolfees} -----------')

        return search_schoolfees, searchbar_inputs

    @staticmethod
    def paymenthistory(search='', search_in='all'):
        searchbar_inputs = {
            'all': {'label': 'Tout', 'input': 'all', 'domain': []},
        }
        if search_in not in searchbar_inputs.keys():
            search_in = 'all'
        search_domain = searchbar_inputs[search_in]['domain']

        order = 'date_from asc'

        search_paymenthistories = []
        if http.request.env.user.employee_id.id:
            user = http.request.env.user.employee_id
            search_domain.append(('employee_id', '=', user.id))

            paymenthistories = http.request.env['hr.payslip'].sudo().search(search_domain, order=order)
            paymenthistories = list(paymenthistories)
            search_paymenthistories = paymenthistories

        _logger.info(f'----------- tototototototo search_paymenthistories {search_paymenthistories} -----------')

        return search_paymenthistories, searchbar_inputs

    @staticmethod
    def notification(search='', search_in='all'):
        searchbar_inputs = {
            'all': {'label': 'Tout', 'input': 'all', 'domain': []},
        }
        if search_in not in searchbar_inputs.keys():
            search_in = 'all'
        search_domain = searchbar_inputs[search_in]['domain']

        order = 'date asc'

        search_notifications = []
        if http.request.env.user.employee_id.id:
            user = http.request.env.user.employee_id
            search_domain.append(('employee_id', '=', user.id))

            notifications = http.request.env['siantou.ems.timetable.notification'].sudo().search(search_domain, order=order)
            notifications = list(notifications)
            search_notifications = notifications

        _logger.info(f'----------- tototototototo search_notifications {search_notifications} -----------')

        return search_notifications, searchbar_inputs

    @staticmethod
    def format_timetable(data):
        timetables = {}
        df = {}

        for d in data:
            d['start_time'] = float(d['start_time'])
            d['end_time'] = float(d['end_time'])
            if d['date'].weekday() == 0:
                monday = d['date']
            else:
                monday = d['date'] - timedelta(days=d['date'].weekday())
            monday = datetime.strftime(monday, DATE_FORMAT)
            if not monday in timetables:
                timetables[monday] = {
                    'Heure': [hour for hour in CURRENT_HOUR],
                    'Lundi': [],
                    'Mardi': [],
                    'Mercredi': [],
                    'Jeudi': [],
                    'Vendredi': [],
                    'Samedi': [],
                    'Dimanche': [],
                }

                for hour in timetables[monday]['Heure']:
                    for key in timetables[monday].keys():
                        if key == 'Heure':
                            continue
                        timetables[monday][key].append(np.nan)
            if not monday in df:
                df[monday] = pd.DataFrame(timetables[monday], dtype=str)
            while d['start_time'] < d['end_time']:
                h = '{}-{}'.format(d['start_time'], (d['start_time'] + 2.0))
                for i, row in df[monday].iterrows():
                    if h == timetables[monday]['Heure'][i]:
                        for j, column in enumerate(df[monday].columns):
                            for k, key in enumerate(timetables[monday].keys()):
                                if k == d['date'].weekday() + 1:
                                    if column == key:
                                        # df[monday].loc[i, column] = d['subject_name']
                                        df[monday].loc[i, column] = d['id']
                                    break
                d['start_time'] += 2.0

        for monday in df.keys():
            df[monday].replace(np.nan, '-', inplace=True)

            for key in timetables[monday].keys():
                timetables[monday][key] = list(df[monday][key])
                if key != 'Heure':
                    for i, v in enumerate(timetables[monday][key]):
                        if v == '-':
                            timetables[monday][key][i] = ''
                        else:
                            timetables[monday][key][i] = [d for d in data if d['id'] == int(v)][0]

            monday = datetime.strptime(f'{monday}', DATE_FORMAT).date()
            sunday = monday + timedelta(days=6)
            monday_fr = datetime.strftime(monday, DATE_FORMAT_FR)
            sunday_fr = datetime.strftime(sunday, DATE_FORMAT_FR)
            monday = datetime.strftime(monday, DATE_FORMAT)
            sunday = '{} - {}'.format(monday_fr, sunday_fr)
            timetables[sunday] = timetables[monday]
            del(timetables[monday])

        _logger.info(f'----------- tototototototo timetables {timetables} -----------')

        return timetables

    @staticmethod
    def convert_float_to_time(tm):
        tm = str(tm)
        tm = tm.split('.')
        if len(tm[0]) == 1:
            tm[0] = '0{}'.format(tm[0])
        if len(tm[1]) == 1:
            tm[1] = '{}0'.format(tm[1])
        tm = ':'.join(tm)
        return tm

    @staticmethod
    def paginate_calendar(items, page_size=10, page_number=1):
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
    def paginate_list(items, page_size=10, page_number=1):
        pages_total = [items[i:i+page_size] for i in range(0, len(items), page_size)]
        start_index = (page_number - 1) * page_size
        end_index = start_index + page_size
        pages = items[start_index:end_index]
        return {
            'total': len(items),
            'pages_total': len(pages_total),
            'pages': pages,
        }
