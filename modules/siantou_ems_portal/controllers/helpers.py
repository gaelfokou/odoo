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
    def timetable(search=None, search_in='all', sortby=None):
        if not search:
            search = ''
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

        searchbar_sortings = {
            'date-desc': {'label': 'Date desc', 'order': 'date desc'},
            'date-asc': {'label': 'Date asc', 'order': 'date asc'},
        }
        if not sortby or sortby not in searchbar_sortings.keys():
            sortby = 'date-desc'
        order = searchbar_sortings[sortby]['order']

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

        return search_timetables, searchbar_inputs, search_in, sortby, searchbar_sortings

    @staticmethod
    def schoolfee(search=None, search_in='all', sortby=None):
        if not search:
            search = ''
        searchbar_inputs = {
            'all': {'label': 'Tout', 'input': 'all', 'domain': []},
        }
        if search_in not in searchbar_inputs.keys():
            search_in = 'all'
        search_domain = searchbar_inputs[search_in]['domain']

        searchbar_sortings = {
            'date-desc': {'label': 'Date desc', 'order': 'date_payment desc'},
            'date-asc': {'label': 'Date asc', 'order': 'date_payment asc'},
        }
        if not sortby or sortby not in searchbar_sortings.keys():
            sortby = 'date-desc'
        order = searchbar_sortings[sortby]['order']

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

        return search_schoolfees, searchbar_inputs, search_in, sortby, searchbar_sortings

    @staticmethod
    def paymenthistory(search=None, search_in='all', sortby=None):
        if not search:
            search = ''
        searchbar_inputs = {
            'all': {'label': 'Tout', 'input': 'all', 'domain': []},
        }
        if search_in not in searchbar_inputs.keys():
            search_in = 'all'
        search_domain = searchbar_inputs[search_in]['domain']

        searchbar_sortings = {
            'date-desc': {'label': 'Date desc', 'order': 'date_from desc'},
            'date-asc': {'label': 'Date asc', 'order': 'date_from asc'},
        }
        if not sortby or sortby not in searchbar_sortings.keys():
            sortby = 'date-desc'
        order = searchbar_sortings[sortby]['order']

        search_paymenthistories = []
        if http.request.env.user.employee_id.id:
            user = http.request.env.user.employee_id
            search_domain.append(('employee_id', '=', user.id))

            paymenthistories = http.request.env['hr.payslip'].sudo().search(search_domain, order=order)
            paymenthistories = list(paymenthistories)
            search_paymenthistories = paymenthistories

        _logger.info(f'----------- tototototototo search_paymenthistories {search_paymenthistories} -----------')

        return search_paymenthistories, searchbar_inputs, search_in, sortby, searchbar_sortings

    @staticmethod
    def format_timetable(data):
        timetables = {
            'Heure': [hour for hour in CURRENT_HOUR],
            'Lundi': [],
            'Mardi': [],
            'Mercredi': [],
            'Jeudi': [],
            'Vendredi': [],
            'Samedi': [],
            'Dimanche': [],
        }

        for hour in timetables['Heure']:
            for key in timetables.keys():
                if key == 'Heure':
                    continue
                timetables[key].append(np.nan)

        df = pd.DataFrame(timetables, dtype=str)

        for d in data:
            d['start_time'] = float(d['start_time'])
            d['end_time'] = float(d['end_time'])
            while d['start_time'] < d['end_time']:
                h = '{}-{}'.format(d['start_time'], (d['start_time'] + 2.0))
                for i, row in df.iterrows():
                    if h == timetables['Heure'][i]:
                        for j, column in enumerate(df.columns):
                            dt = d['date']
                            for k, key in enumerate(timetables.keys()):
                                if k == dt.weekday() + 1:
                                    if column == key:
                                        # df.loc[i, column] = d['subject_name']
                                        df.loc[i, column] = d['id']
                                    break
                d['start_time'] += 2.0

        df.replace(np.nan, '-', inplace=True)

        for key in timetables.keys():
            timetables[key] = list(df[key])
            if key != 'Heure':
                for i, v in enumerate(timetables[key]):
                    if v == '-':
                        timetables[key][i] = ''
                    else:
                        timetables[key][i] = [d for d in data if d['id'] == int(v)][0]

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
