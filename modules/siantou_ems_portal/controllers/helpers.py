# helpers.py
from odoo import http
from odoo.addons.portal.controllers import portal
from odoo.exceptions import UserError, ValidationError
import pandas as pd
import numpy as np
import re
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import pytz
import logging
import copy

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

STATUS_TIMETABLE = {
    'pending': 'En attente',
    'progress': 'En cours',
    'present': 'Présent',
    'absent': 'Absent',
    'permission': 'Permission',
    'exception': 'Exception',
    'delay': 'Retard',
}

CURRENT_MONTH = {
    '1': 'Janvier',
    '2': 'Février',
    '3': 'Mars',
    '4': 'Avril',
    '5': 'Mai',
    '6': 'Juin',
    '7': 'Juillet',
    '8': 'Août',
    '9': 'Septembre',
    '10': 'Octobre',
    '11': 'Novembre',
    '12': 'Décembre',
}

_logger = logging.getLogger(__name__)

class Helpers:
    @staticmethod
    def timetable(search='', search_in='all', selected_month='0', cycle_id=None, level_id=None, field_of_study_id=None, specialty_id=None, option_id=None, class_id=None):
        searchbar_inputs = {
            'all': {'label': 'Tout', 'input': 'all', 'domain': []},
            'cycle': {'label': 'Cycle', 'input': 'cycle', 'domain': [('cycle_id.name', 'like', search)]},
            'niveau': {'label': 'Niveau', 'input': 'niveau', 'domain': [('level_id.name', 'like', search)]},
            'filiere': {'label': 'Filière', 'input': 'filiere', 'domain': [('field_of_study_id.name', 'like', search)]},
            'specialite': {'label': 'Spécialité', 'input': 'specialite', 'domain': [('specialty_id.name', 'like', search)]},
            'option': {'label': 'Option', 'input': 'option', 'domain': [('option_id.name', 'like', search)]},
            'classe': {'label': 'Classe', 'input': 'classe', 'domain': [('class_id.name', 'like', search)]},
            'cours': {'label': 'Cours', 'input': 'cours', 'domain': [('subject_id.name', 'like', search)]},
            'enseignant': {'label': 'Enseignant', 'input': 'enseignant', 'domain': [('employee_id.name', 'like', search)]},
        }
        if search_in not in searchbar_inputs.keys():
            search_in = 'all'
        search_domain = searchbar_inputs[search_in]['domain']

        if cycle_id:
            search_domain.append(('cycle_id', '=', cycle_id.id))
        if level_id:
            search_domain.append(('level_id', '=', level_id.id))
        if field_of_study_id:
            search_domain.append(('field_of_study_id', '=', field_of_study_id.id))
        if specialty_id:
            search_domain.append(('specialty_id', '=', specialty_id.id))
        if option_id:
            search_domain.append(('option_id', '=', option_id.id))
        if class_id:
            search_domain.append(('class_id', '=', class_id.id))

        search_domain.append('|')
        search_domain.append('&')
        search_domain.append(('group_id.is_active', '=', True))
        search_domain.append(('group_id.is_submit', '=', False))
        search_domain.append('&')
        search_domain.append(('group_parent_id.is_active', '=', True))
        search_domain.append(('group_parent_id.is_submit', '=', False))

        order = 'date asc, id asc'

        search_month = ''
        search_timetables = []
        user = None
        is_user = None
        if http.request.env.user.employee_id.id:
            user = http.request.env.user.employee_id
            if http.request.env.user.employee_id.is_teacher:
                is_user = 'is_teacher'
            else:
                is_user = 'is_employee'
        elif http.request.env.user.student_id.id:
            user = http.request.env.user.student_id
            is_user = 'is_student'
        if is_user:
            if is_user == 'is_teacher':
                user = http.request.env.user.employee_id
                search_domain.append(('employee_id', '=', user.id))

                timetables = http.request.env['siantou.ems.timetable.timetable'].sudo().search(search_domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                current_date = date.today()
                current_date = current_date - relativedelta(day=1, months=int(selected_month))
                start_date = current_date + relativedelta(day=1)
                end_date = current_date + relativedelta(day=1, months=1, days=-1)
                if start_date and end_date:
                    timetables = timetables.filtered(lambda rec: rec.date and rec.day_of_week and rec.date >= start_date and rec.date <= end_date)
                timetables = list(timetables)
                key_timetables = {}
                for timetable in timetables:
                    if not timetable.date or not timetable.day_of_week or not timetable.employee_id.id:
                        continue

                    end_time = Helpers.convert_float_to_time(timetable.end_time, True)
                    start_time = Helpers.convert_float_to_time(timetable.start_time, True)
                    key = '{}-{}-{}-{}-{}'.format(timetable.employee_id.id, timetable.class_id.id, timetable.date, start_time, end_time)
                    if key not in key_timetables:
                        key_timetables[key] = timetable
                    else:
                        continue

                    search_timetables.append(timetable)

                start_date = datetime.strftime(start_date, DATE_FORMAT_FR)
                end_date = datetime.strftime(end_date, DATE_FORMAT_FR)
                search_month = '{} - {}'.format(start_date, end_date)
            elif is_user == 'is_student':
                search_domain.append(('class_id', '=', user.class_id.id))

                timetables = http.request.env['siantou.ems.timetable.timetable'].sudo().search(search_domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                current_date = date.today()
                current_date = current_date - relativedelta(day=1, months=int(selected_month))
                start_date = current_date + relativedelta(day=1)
                end_date = current_date + relativedelta(day=1, months=1, days=-1)
                if start_date and end_date:
                    timetables = timetables.filtered(lambda rec: rec.date and rec.day_of_week and rec.date >= start_date and rec.date <= end_date)
                timetables = list(timetables)
                key_timetables = {}
                for timetable in timetables:
                    if not timetable.date or not timetable.day_of_week or not timetable.employee_id.id:
                        continue

                    end_time = Helpers.convert_float_to_time(timetable.end_time, True)
                    start_time = Helpers.convert_float_to_time(timetable.start_time, True)
                    key = '{}-{}-{}-{}'.format(timetable.class_id.id, timetable.date, start_time, end_time)
                    if key not in key_timetables:
                        key_timetables[key] = timetable
                    else:
                        continue

                    search_timetables.append(timetable)

                start_date = datetime.strftime(start_date, DATE_FORMAT_FR)
                end_date = datetime.strftime(end_date, DATE_FORMAT_FR)
                search_month = '{} - {}'.format(start_date, end_date)

        _logger.info(f'----------- tototototototo search_timetables {search_timetables} -----------')

        return search_timetables, searchbar_inputs, search_month

    @staticmethod
    def schoolfee(search='', search_in='all'):
        searchbar_inputs = {
            'all': {'label': 'Tout', 'input': 'all', 'domain': []},
        }
        if search_in not in searchbar_inputs.keys():
            search_in = 'all'
        search_domain = searchbar_inputs[search_in]['domain']

        order = 'date_payment asc'

        search_schoolfees = []
        if http.request.env.user.student_id.id:
            user = http.request.env.user.student_id
            search_domain.append(('student_id', '=', user.id))

            schoolfees = http.request.env['education.fee.payment'].sudo().search(search_domain, order=order)
            schoolfees = list(schoolfees)
            search_schoolfees = schoolfees

            search_domain = []
            search_domain.append(('student_id', '=', user.id))

            schoolfees = http.request.env['education.fee.payment.enrollment'].sudo().search(search_domain, order=order)
            schoolfees = list(schoolfees)
            search_schoolfees += schoolfees

        _logger.info(f'----------- tototototototo search_schoolfees {search_schoolfees} -----------')

        return search_schoolfees, searchbar_inputs

    @staticmethod
    def examscore(search='', search_in='all'):
        searchbar_inputs = {
            'all': {'label': 'Tout', 'input': 'all', 'domain': []},
        }
        if search_in not in searchbar_inputs.keys():
            search_in = 'all'

        search_domain = searchbar_inputs[search_in]['domain']

        # search_domain.append(('status', '=', 'end'))

        order = 'id asc'

        search_examscores = []
        if http.request.env.user.student_id.id:
            user = http.request.env.user.student_id
            search_domain.append(('class_id', '=', user.class_id.id))

            examscores = http.request.env['siantou.ems.core.exam.score'].sudo().search(search_domain, order=order)
            examscores = list(examscores)
            for examscore in examscores:
                search_examscores.append(examscore)

        _logger.info(f'----------- tototototototo search_examscores {search_examscores} -----------')

        return search_examscores, searchbar_inputs

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
            if http.request.env.user.employee_id.is_teacher:
                user = http.request.env.user.employee_id
                search_domain.append(('employee_id', '=', user.id))

                paymenthistories = http.request.env['hr.payslip'].sudo().search(search_domain, order=order)
                paymenthistories = list(paymenthistories)
                search_paymenthistories = paymenthistories

        _logger.info(f'----------- tototototototo search_paymenthistories {search_paymenthistories} -----------')

        return search_paymenthistories, searchbar_inputs

    @staticmethod
    def accountbalance(search='', search_in='all', selected_month='0', cycle_id=None, level_id=None, field_of_study_id=None, specialty_id=None, option_id=None, class_id=None, end_date=None, start_date=None):
        searchbar_inputs = {
            'all': {'label': 'Tout', 'input': 'all', 'domain': []},
            'cycle': {'label': 'Cycle', 'input': 'cycle', 'domain': [('cycle_id.name', 'like', search)]},
            'niveau': {'label': 'Niveau', 'input': 'niveau', 'domain': [('level_id.name', 'like', search)]},
            'filiere': {'label': 'Filière', 'input': 'filiere', 'domain': [('field_of_study_id.name', 'like', search)]},
            'specialite': {'label': 'Spécialité', 'input': 'specialite', 'domain': [('specialty_id.name', 'like', search)]},
            'option': {'label': 'Option', 'input': 'option', 'domain': [('option_id.name', 'like', search)]},
            'classe': {'label': 'Classe', 'input': 'classe', 'domain': [('class_id.name', 'like', search)]},
            'cours': {'label': 'Cours', 'input': 'cours', 'domain': [('subject_id.name', 'like', search)]},
            'enseignant': {'label': 'Enseignant', 'input': 'enseignant', 'domain': [('employee_id.name', 'like', search)]},
        }
        if search_in not in searchbar_inputs.keys():
            search_in = 'all'
        search_domain = searchbar_inputs[search_in]['domain']

        if cycle_id:
            search_domain.append(('cycle_id', '=', cycle_id.id))
        if level_id:
            search_domain.append(('level_id', '=', level_id.id))
        if field_of_study_id:
            search_domain.append(('field_of_study_id', '=', field_of_study_id.id))
        if specialty_id:
            search_domain.append(('specialty_id', '=', specialty_id.id))
        if option_id:
            search_domain.append(('option_id', '=', option_id.id))
        if class_id:
            search_domain.append(('class_id', '=', class_id.id))

        search_domain.append('|')
        search_domain.append('&')
        search_domain.append(('group_id.is_active', '=', True))
        search_domain.append(('group_id.is_submit', '=', False))
        search_domain.append('&')
        search_domain.append(('group_parent_id.is_active', '=', True))
        search_domain.append(('group_parent_id.is_submit', '=', False))
        search_domain.append(('status', 'in', ['present', 'permission']))

        order = 'date asc, id asc'

        search_month = ''
        search_accountbalances = []
        if http.request.env.user.employee_id.id:
            if http.request.env.user.employee_id.is_teacher:
                user = http.request.env.user.employee_id
                search_domain.append(('employee_id', '=', user.id))

                accountbalances = http.request.env['siantou.ems.timetable.timetable'].sudo().search(search_domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                current_date = date.today()
                current_date = current_date - relativedelta(day=1, months=int(selected_month))
                start_date = current_date + relativedelta(day=1)
                end_date = current_date + relativedelta(day=1, months=1, days=-1)
                if start_date and end_date:
                    accountbalances = accountbalances.filtered(lambda rec: rec.date and rec.day_of_week and rec.date >= start_date and rec.date <= end_date)
                accountbalances = list(accountbalances)
                key_accountbalances = {}
                for accountbalance in accountbalances:
                    if not accountbalance.date or not accountbalance.day_of_week or not accountbalance.employee_id.id:
                        continue

                    end_time = Helpers.convert_float_to_time(accountbalance.end_time, True)
                    start_time = Helpers.convert_float_to_time(accountbalance.start_time, True)
                    key = '{}-{}-{}-{}'.format(accountbalance.employee_id.id, accountbalance.date, start_time, end_time)
                    if key not in key_accountbalances:
                        key_accountbalances[key] = accountbalance
                    else:
                        continue

                    search_accountbalances.append(accountbalance)

                start_date = datetime.strftime(start_date, DATE_FORMAT_FR)
                end_date = datetime.strftime(end_date, DATE_FORMAT_FR)
                search_month = '{} - {}'.format(start_date, end_date)

        _logger.info(f'----------- tototototototo search_accountbalances {search_accountbalances} -----------')

        return search_accountbalances, searchbar_inputs, search_month

    @staticmethod
    def consumptionhour(search='', search_in='all', cycle_id=None, level_id=None, field_of_study_id=None, specialty_id=None, option_id=None, class_id=None):
        searchbar_inputs = {
            'all': {'label': 'Tout', 'input': 'all', 'domain': []},
            'cycle': {'label': 'Cycle', 'input': 'cycle', 'domain': [('cycle_id.name', 'like', search)]},
            'niveau': {'label': 'Niveau', 'input': 'niveau', 'domain': [('level_id.name', 'like', search)]},
            'filiere': {'label': 'Filière', 'input': 'filiere', 'domain': [('field_of_study_id.name', 'like', search)]},
            'specialite': {'label': 'Spécialité', 'input': 'specialite', 'domain': [('specialty_id.name', 'like', search)]},
            'option': {'label': 'Option', 'input': 'option', 'domain': [('option_id.name', 'like', search)]},
            'classe': {'label': 'Classe', 'input': 'classe', 'domain': [('class_id.name', 'like', search)]},
            'cours': {'label': 'Cours', 'input': 'cours', 'domain': [('subject_id.name', 'like', search)]},
            'enseignant': {'label': 'Enseignant', 'input': 'enseignant', 'domain': [('employee_id.name', 'like', search)]},
        }
        if search_in not in searchbar_inputs.keys():
            search_in = 'all'
        search_domain = searchbar_inputs[search_in]['domain']

        if cycle_id:
            search_domain.append(('cycle_id', '=', cycle_id.id))
        if level_id:
            search_domain.append(('level_id', '=', level_id.id))
        if field_of_study_id:
            search_domain.append(('field_of_study_id', '=', field_of_study_id.id))
        if specialty_id:
            search_domain.append(('specialty_id', '=', specialty_id.id))
        if option_id:
            search_domain.append(('option_id', '=', option_id.id))
        if class_id:
            search_domain.append(('class_id', '=', class_id.id))

        search_domain.append('|')
        search_domain.append('&')
        search_domain.append(('group_id.is_active', '=', True))
        search_domain.append(('group_id.is_submit', '=', False))
        search_domain.append('&')
        search_domain.append(('group_parent_id.is_active', '=', True))
        search_domain.append(('group_parent_id.is_submit', '=', False))
        search_domain.append(('status', 'in', ['present', 'permission']))

        order = 'date asc, id asc'

        search_consumptionhours = []
        user = None
        is_user = None
        if http.request.env.user.employee_id.id:
            user = http.request.env.user.employee_id
            if http.request.env.user.employee_id.is_teacher:
                is_user = 'is_teacher'
            else:
                is_user = 'is_employee'
        elif http.request.env.user.student_id.id:
            user = http.request.env.user.student_id
            is_user = 'is_student'
        if is_user:
            if is_user == 'is_teacher':
                user = http.request.env.user.employee_id
                search_domain.append(('employee_id', '=', user.id))

                consumptionhours = http.request.env['siantou.ems.timetable.timetable'].sudo().search(search_domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                consumptionhours = list(consumptionhours)
                key_consumptionhours = {}
                for consumptionhour in consumptionhours:
                    if not consumptionhour.date or not consumptionhour.day_of_week or not consumptionhour.employee_id.id:
                        continue

                    end_time = Helpers.convert_float_to_time(consumptionhour.end_time, True)
                    start_time = Helpers.convert_float_to_time(consumptionhour.start_time, True)
                    key = '{}-{}-{}-{}-{}'.format(consumptionhour.employee_id.id, consumptionhour.class_id.id, consumptionhour.date, start_time, end_time)
                    if key not in key_consumptionhours:
                        key_consumptionhours[key] = consumptionhour
                    else:
                        continue

                    search_consumptionhours.append(consumptionhour)
            elif is_user == 'is_student':
                search_domain.append(('class_id', '=', user.class_id.id))

                consumptionhours = http.request.env['siantou.ems.timetable.timetable'].sudo().search(search_domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                consumptionhours = list(consumptionhours)
                key_consumptionhours = {}
                for consumptionhour in consumptionhours:
                    if not consumptionhour.date or not consumptionhour.day_of_week or not consumptionhour.employee_id.id:
                        continue

                    end_time = Helpers.convert_float_to_time(consumptionhour.end_time, True)
                    start_time = Helpers.convert_float_to_time(consumptionhour.start_time, True)
                    key = '{}-{}-{}-{}'.format(consumptionhour.class_id.id, consumptionhour.date, start_time, end_time)
                    if key not in key_consumptionhours:
                        key_consumptionhours[key] = consumptionhour
                    else:
                        continue

                    search_consumptionhours.append(consumptionhour)

        _logger.info(f'----------- tototototototo search_consumptionhours {search_consumptionhours} -----------')

        return search_consumptionhours, searchbar_inputs

    @staticmethod
    def progressreport(search='', search_in='all', cycle_id=None, level_id=None, field_of_study_id=None, specialty_id=None, option_id=None, class_id=None):
        searchbar_inputs = {
            'all': {'label': 'Tout', 'input': 'all', 'domain': []},
            'cycle': {'label': 'Cycle', 'input': 'cycle', 'domain': [('cycle_id.name', 'like', search)]},
            'niveau': {'label': 'Niveau', 'input': 'niveau', 'domain': [('level_id.name', 'like', search)]},
            'filiere': {'label': 'Filière', 'input': 'filiere', 'domain': [('field_of_study_id.name', 'like', search)]},
            'specialite': {'label': 'Spécialité', 'input': 'specialite', 'domain': [('specialty_id.name', 'like', search)]},
            'option': {'label': 'Option', 'input': 'option', 'domain': [('option_id.name', 'like', search)]},
            'classe': {'label': 'Classe', 'input': 'classe', 'domain': [('class_id.name', 'like', search)]},
            'cours': {'label': 'Cours', 'input': 'cours', 'domain': [('subject_id.name', 'like', search)]},
            'enseignant': {'label': 'Enseignant', 'input': 'enseignant', 'domain': [('employee_id.name', 'like', search)]},
        }
        if search_in not in searchbar_inputs.keys():
            search_in = 'all'
        search_domain = searchbar_inputs[search_in]['domain']

        if cycle_id:
            search_domain.append(('cycle_id', '=', cycle_id.id))
        if level_id:
            search_domain.append(('level_id', '=', level_id.id))
        if field_of_study_id:
            search_domain.append(('field_of_study_id', '=', field_of_study_id.id))
        if specialty_id:
            search_domain.append(('specialty_id', '=', specialty_id.id))
        if option_id:
            search_domain.append(('option_id', '=', option_id.id))
        if class_id:
            search_domain.append(('class_id', '=', class_id.id))

        search_domain.append('|')
        search_domain.append('&')
        search_domain.append(('group_id.is_active', '=', True))
        search_domain.append(('group_id.is_submit', '=', False))
        search_domain.append('&')
        search_domain.append(('group_parent_id.is_active', '=', True))
        search_domain.append(('group_parent_id.is_submit', '=', False))

        order = 'date asc, id asc'

        search_progressreports = []
        user = None
        is_user = None
        if http.request.env.user.employee_id.id:
            user = http.request.env.user.employee_id
            if http.request.env.user.employee_id.is_teacher:
                is_user = 'is_teacher'
            else:
                is_user = 'is_employee'
        elif http.request.env.user.student_id.id:
            user = http.request.env.user.student_id
            is_user = 'is_student'
        if is_user:
            if is_user == 'is_teacher':
                user = http.request.env.user.employee_id
                search_domain.append(('employee_id', '=', user.id))

                progressreports = http.request.env['siantou.ems.timetable.timetable'].sudo().search(search_domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                progressreports = list(progressreports)
                key_progressreports = {}
                for progressreport in progressreports:
                    if not progressreport.date or not progressreport.day_of_week or not progressreport.employee_id.id:
                        continue

                    end_time = Helpers.convert_float_to_time(progressreport.end_time, True)
                    start_time = Helpers.convert_float_to_time(progressreport.start_time, True)
                    key = '{}-{}-{}-{}-{}'.format(progressreport.employee_id.id, progressreport.class_id.id, progressreport.date, start_time, end_time)
                    if key not in key_progressreports:
                        key_progressreports[key] = progressreport
                    else:
                        continue

                    search_progressreports.append(progressreport)
            elif is_user == 'is_student':
                search_domain.append(('class_id', '=', user.class_id.id))

                progressreports = http.request.env['siantou.ems.timetable.timetable'].sudo().search(search_domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                progressreports = list(progressreports)
                key_progressreports = {}
                for progressreport in progressreports:
                    if not progressreport.date or not progressreport.day_of_week or not progressreport.employee_id.id:
                        continue

                    end_time = Helpers.convert_float_to_time(progressreport.end_time, True)
                    start_time = Helpers.convert_float_to_time(progressreport.start_time, True)
                    key = '{}-{}-{}-{}'.format(progressreport.class_id.id, progressreport.date, start_time, end_time)
                    if key not in key_progressreports:
                        key_progressreports[key] = progressreport
                    else:
                        continue

                    search_progressreports.append(progressreport)

        _logger.info(f'----------- tototototototo search_progressreports {search_progressreports} -----------')

        return search_progressreports, searchbar_inputs

    @staticmethod
    def report(search='', search_in='all', class_id=None, subject_id=None):
        searchbar_inputs = {
            'all': {'label': 'Tout', 'input': 'all', 'domain': []},
            'classe': {'label': 'Classe', 'input': 'classe', 'domain': [('class_id.name', 'like', search)]},
            'cours': {'label': 'Cours', 'input': 'cours', 'domain': [('subject_id.name', 'like', search)]},
        }
        if search_in not in searchbar_inputs.keys():
            search_in = 'all'
        search_domain = searchbar_inputs[search_in]['domain']

        if class_id:
            search_domain.append(('class_id', '=', class_id.id))
        if subject_id:
            search_domain.append(('subject_id', '=', subject_id.id))

        order = 'id asc'

        search_reports = []
        reports = http.request.env['siantou.ems.core.progress.report'].sudo().search(search_domain, order=order).sorted(lambda rec: rec.id)
        reports = list(reports)
        for report in reports:
            search_reports.append(report)

        _logger.info(f'----------- tototototototo search_reports {search_reports} -----------')

        return search_reports, searchbar_inputs

    @staticmethod
    def subjectsession(search='', search_in='all', cycle_id=None, level_id=None, field_of_study_id=None, specialty_id=None, option_id=None, class_id=None, subject_id=None):
        searchbar_inputs = {
            'all': {'label': 'Tout', 'input': 'all', 'domain': []},
            'cycle': {'label': 'Cycle', 'input': 'cycle', 'domain': [('cycle_id.name', 'like', search)]},
            'niveau': {'label': 'Niveau', 'input': 'niveau', 'domain': [('level_id.name', 'like', search)]},
            'filiere': {'label': 'Filière', 'input': 'filiere', 'domain': [('field_of_study_id.name', 'like', search)]},
            'specialite': {'label': 'Spécialité', 'input': 'specialite', 'domain': [('specialty_id.name', 'like', search)]},
            'option': {'label': 'Option', 'input': 'option', 'domain': [('option_id.name', 'like', search)]},
            'classe': {'label': 'Classe', 'input': 'classe', 'domain': [('class_id.name', 'like', search)]},
            'cours': {'label': 'Cours', 'input': 'cours', 'domain': [('subject_id.name', 'like', search)]},
            'enseignant': {'label': 'Enseignant', 'input': 'enseignant', 'domain': [('employee_id.name', 'like', search)]},
        }
        if search_in not in searchbar_inputs.keys():
            search_in = 'all'
        search_domain = searchbar_inputs[search_in]['domain']

        if cycle_id:
            search_domain.append(('cycle_id', '=', cycle_id.id))
        if level_id:
            search_domain.append(('level_id', '=', level_id.id))
        if field_of_study_id:
            search_domain.append(('field_of_study_id', '=', field_of_study_id.id))
        if specialty_id:
            search_domain.append(('specialty_id', '=', specialty_id.id))
        if option_id:
            search_domain.append(('option_id', '=', option_id.id))
        if class_id:
            search_domain.append(('class_id', '=', class_id.id))
        if subject_id:
            search_domain.append(('subject_id', '=', subject_id.id))

        search_domain.append('|')
        search_domain.append('&')
        search_domain.append(('group_id.is_active', '=', True))
        search_domain.append(('group_id.is_submit', '=', False))
        search_domain.append('&')
        search_domain.append(('group_parent_id.is_active', '=', True))
        search_domain.append(('group_parent_id.is_submit', '=', False))

        order = 'date asc, id asc'

        search_subjectsessions = []
        user = None
        is_user = None
        if http.request.env.user.employee_id.id:
            user = http.request.env.user.employee_id
            if http.request.env.user.employee_id.is_teacher:
                is_user = 'is_teacher'
            else:
                is_user = 'is_employee'
        elif http.request.env.user.student_id.id:
            user = http.request.env.user.student_id
            is_user = 'is_student'
        if is_user:
            if is_user == 'is_teacher':
                user = http.request.env.user.employee_id
                search_domain.append(('employee_id', '=', user.id))

                subjectsessions = http.request.env['siantou.ems.timetable.timetable'].sudo().search(search_domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                subjectsessions = list(subjectsessions)
                key_subjectsessions = {}
                for subjectsession in subjectsessions:
                    if not subjectsession.date or not subjectsession.day_of_week or not subjectsession.employee_id.id:
                        continue

                    end_time = Helpers.convert_float_to_time(subjectsession.end_time, True)
                    start_time = Helpers.convert_float_to_time(subjectsession.start_time, True)
                    key = '{}-{}-{}-{}-{}'.format(subjectsession.employee_id.id, subjectsession.class_id.id, subjectsession.date, start_time, end_time)
                    if key not in key_subjectsessions:
                        key_subjectsessions[key] = subjectsession
                    else:
                        continue

                    search_subjectsessions.append(subjectsession)
            elif is_user == 'is_student':
                search_domain.append(('class_id', '=', user.class_id.id))

                subjectsessions = http.request.env['siantou.ems.timetable.timetable'].sudo().search(search_domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                subjectsessions = list(subjectsessions)
                key_subjectsessions = {}
                for subjectsession in subjectsessions:
                    if not subjectsession.date or not subjectsession.day_of_week or not subjectsession.employee_id.id:
                        continue

                    end_time = Helpers.convert_float_to_time(subjectsession.end_time, True)
                    start_time = Helpers.convert_float_to_time(subjectsession.start_time, True)
                    key = '{}-{}-{}-{}'.format(subjectsession.class_id.id, subjectsession.date, start_time, end_time)
                    if key not in key_subjectsessions:
                        key_subjectsessions[key] = subjectsession
                    else:
                        continue

                    search_subjectsessions.append(subjectsession)

        _logger.info(f'----------- tototototototo search_subjectsessions {search_subjectsessions} -----------')

        return search_subjectsessions, searchbar_inputs

    @staticmethod
    def calendar(search='', search_in='all'):
        searchbar_inputs = {
            'all': {'label': 'Tout', 'input': 'all', 'domain': []},
        }
        if search_in not in searchbar_inputs.keys():
            search_in = 'all'
        search_domain = searchbar_inputs[search_in]['domain']

        order = 'start_date asc'

        year_id = http.request.env['siantou.ems.core.year'].sudo().search([('is_active', '=', True)], limit=1)
        if year_id:
            search_year = year_id.name.split('-')
            search_year = [int(y) for y in search_year]
        else:
            search_year = []
        calendars = http.request.env['calendar.event'].sudo().search(search_domain, order=order)
        calendars = calendars.filtered(lambda rec: rec.start.year in search_year)
        calendars = list(calendars)
        search_calendars = calendars

        _logger.info(f'----------- tototototototo search_calendars {search_calendars} -----------')

        return search_calendars, searchbar_inputs, search_year

    @staticmethod
    def notification(search='', search_in='all'):
        searchbar_inputs = {
            'all': {'label': 'Tout', 'input': 'all', 'domain': []},
        }
        if search_in not in searchbar_inputs.keys():
            search_in = 'all'
        search_domain = searchbar_inputs[search_in]['domain']

        order = 'date desc, id desc'

        search_notifications = []
        if http.request.env.user.employee_id.id:
            if http.request.env.user.employee_id.is_teacher:
                user = http.request.env.user.employee_id
                search_domain.append(('employee_id', '=', user.id))

                notifications = http.request.env['siantou.ems.timetable.notification'].sudo().search(search_domain, order=order).sorted(lambda rec: (rec.date, rec.id), reverse=True)
                notifications = list(notifications)
                search_notifications = notifications

        _logger.info(f'----------- tototototototo search_notifications {search_notifications} -----------')

        return search_notifications, searchbar_inputs

    @staticmethod
    def is_float(data):
        try:
            float(data)
            return True
        except ValueError:
            return False

    @staticmethod
    def sort_by_indexes(lst, indexes, reverse=False):
        return [val for (_, val) in sorted(zip(indexes, lst), key=lambda x: x[0], reverse=reverse)]

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
                    if not (Helpers.increment_float_time(data[i]['start_time']) <= Helpers.increment_float_time(hour[0]) and Helpers.increment_float_time(data[i]['end_time']) > Helpers.increment_float_time(hour[0])) or not (Helpers.increment_float_time(data[i]['start_time']) < Helpers.increment_float_time(hour[1]) and Helpers.increment_float_time(data[i]['end_time']) >= Helpers.increment_float_time(hour[1])):
                        current_data.append(data[i])
                        break
                    else:
                        if not (Helpers.increment_float_time(data[i]['start_time']) == Helpers.increment_float_time(hour[0]) and Helpers.increment_float_time(data[i]['end_time']) == Helpers.increment_float_time(hour[1])):
                            if not (Helpers.increment_float_time(data[i]['start_time']) < Helpers.increment_float_time(hour[0]) and Helpers.increment_float_time(data[i]['end_time']) > Helpers.increment_float_time(hour[1])):
                                if Helpers.increment_float_time(data[i]['start_time']) == Helpers.increment_float_time(hour[0]):
                                    data[i]['start_time'] = hour[1]
                                    current_data.append(data[i])
                                    break
                                else:
                                    if Helpers.increment_float_time(data[i]['end_time']) == Helpers.increment_float_time(hour[1]):
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
            while Helpers.increment_float_time(hours[i][0]) < Helpers.increment_float_time(hours[i][1]):
                if Helpers.increment_float_time(hours[i][0], n) == 0.0:
                    h = '{}-{}'.format(Helpers.increment_float_time(hours[i][0]), Helpers.increment_float_time(hours[i][1]))
                    current_hours.append(h)
                    hours[i][0] = Helpers.increment_float_time(hours[i][1])
                else:
                    if Helpers.increment_float_time(hours[i][0], n) < Helpers.increment_float_time(hours[i][1]):
                        h = '{}-{}'.format(Helpers.increment_float_time(hours[i][0]), Helpers.increment_float_time(hours[i][0], n))
                    else:
                        h = '{}-{}'.format(Helpers.increment_float_time(hours[i][0]), Helpers.increment_float_time(hours[i][1]))
                    current_hours.append(h)
                    hours[i][0] = Helpers.increment_float_time(hours[i][0], n)

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
            while Helpers.increment_float_time(d['start_time']) < Helpers.increment_float_time(d['end_time']):
                if Helpers.increment_float_time(d['start_time'], n) < Helpers.increment_float_time(d['end_time']):
                    h = '{}-{}'.format(Helpers.increment_float_time(d['start_time']), Helpers.increment_float_time(d['start_time'], n))
                else:
                    h = '{}-{}'.format(Helpers.increment_float_time(d['start_time']), Helpers.increment_float_time(d['end_time']))
                for i, row in df[monday].iterrows():
                    if h == timetables[monday]['Heure'][i]:
                        for j, column in enumerate(df[monday].columns):
                            for k, key in enumerate(timetables[monday].keys()):
                                if k == d['date'].weekday() + 1:
                                    if column == key:
                                        if Helpers.is_float(str(df[monday].loc[i, column])) and np.isnan(float(str(df[monday].loc[i, column]))):
                                            df[monday].loc[i, column] = str(d['id'])
                                        else:
                                            df[monday].loc[i, column] = '{}-{}'.format(df[monday].loc[i, column], str(d['id']))
                                    break
                d['start_time'] = Helpers.increment_float_time(d['start_time'], n)

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

    @staticmethod
    def format_accountbalance(data):
        accountbalances = {}

        sorted_data = copy.deepcopy(data)

        for d in sorted_data:
            key_class = '{}'.format(d['class_id'])
            key_subject = '{}'.format(d['subject_id'])
            if key_class not in accountbalances:
                accountbalances[key_class] = {}
                accountbalances[key_class]['name'] = d['class_name']
                accountbalances[key_class]['data'] = {}
                accountbalances[key_class]['data'][key_subject] = {}
                accountbalances[key_class]['data'][key_subject]['name'] = d['subject_name']
                accountbalances[key_class]['data'][key_subject]['data'] = []
                accountbalances[key_class]['data'][key_subject]['data'].append(d)
            else:
                if key_subject not in accountbalances[key_class]['data']:
                    accountbalances[key_class]['data'][key_subject] = {}
                    accountbalances[key_class]['data'][key_subject]['name'] = d['subject_name']
                    accountbalances[key_class]['data'][key_subject]['data'] = []
                    accountbalances[key_class]['data'][key_subject]['data'].append(d)
                else:
                    accountbalances[key_class]['data'][key_subject]['data'].append(d)

        for key_class in accountbalances.keys():
            accountbalances[key_class]['total_rate'] = 0
            accountbalances[key_class]['total_number_of_hours'] = 0
            for key_subject in accountbalances[key_class]['data'].keys():
                accountbalances[key_class]['data'][key_subject]['amount'] = sum([v['amount'] for v in accountbalances[key_class]['data'][key_subject]['data']])
                accountbalances[key_class]['data'][key_subject]['number_of_hours'] = sum([v['number_of_hours'] for v in accountbalances[key_class]['data'][key_subject]['data']])
                accountbalances[key_class]['total_rate'] += accountbalances[key_class]['data'][key_subject]['amount']
                accountbalances[key_class]['total_number_of_hours'] += accountbalances[key_class]['data'][key_subject]['number_of_hours']

        for key_class in accountbalances.keys():
            accountbalances[key_class]['total_rate'] = round(accountbalances[key_class]['total_rate'], 2)
            accountbalances[key_class]['total_number_of_hours'] = round(accountbalances[key_class]['total_number_of_hours'], 2)

        _logger.info(f'----------- tototototototo accountbalances {accountbalances} -----------')

        return accountbalances

    @staticmethod
    def format_consumptionhour(data):
        consumptionhours = {}

        sorted_data = copy.deepcopy(data)

        for d in sorted_data:
            key_class = '{}'.format(d['class_id'])
            key_subject = '{}'.format(d['subject_id'])
            if key_class not in consumptionhours:
                consumptionhours[key_class] = {}
                consumptionhours[key_class]['name'] = d['class_name']
                consumptionhours[key_class]['data'] = {}
                consumptionhours[key_class]['data'][key_subject] = {}
                consumptionhours[key_class]['data'][key_subject]['name'] = d['subject_name']
                consumptionhours[key_class]['data'][key_subject]['data'] = {
                    'credit': 0,
                    'done': [],
                }
                consumptionhours[key_class]['data'][key_subject]['data']['credit'] = d['subject_hours_credit']
                consumptionhours[key_class]['data'][key_subject]['data']['done'].append(d)
            else:
                if key_subject not in consumptionhours[key_class]['data']:
                    consumptionhours[key_class]['data'][key_subject] = {}
                    consumptionhours[key_class]['data'][key_subject]['name'] = d['subject_name']
                    consumptionhours[key_class]['data'][key_subject]['data'] = {
                        'credit': 0,
                        'done': [],
                    }
                    consumptionhours[key_class]['data'][key_subject]['data']['credit'] = d['subject_hours_credit']
                    consumptionhours[key_class]['data'][key_subject]['data']['done'].append(d)
                else:
                    consumptionhours[key_class]['data'][key_subject]['data']['done'].append(d)

        for key_class in consumptionhours.keys():
            consumptionhours[key_class]['hours_credit'] = 0.0
            consumptionhours[key_class]['total_all'] = 0.0
            consumptionhours[key_class]['total_done'] = 0.0
            consumptionhours[key_class]['total_awaiting'] = 0.0
            for key_subject in consumptionhours[key_class]['data'].keys():
                consumptionhours[key_class]['data'][key_subject]['data']['done'] = sum([Helpers.convert_number_of_hours(v) for v in consumptionhours[key_class]['data'][key_subject]['data']['done']])
                consumptionhours[key_class]['data'][key_subject]['data']['awaiting'] = consumptionhours[key_class]['data'][key_subject]['data']['credit'] - consumptionhours[key_class]['data'][key_subject]['data']['done']
                consumptionhours[key_class]['data'][key_subject]['data']['done'] = round(consumptionhours[key_class]['data'][key_subject]['data']['done'], 2)
                consumptionhours[key_class]['data'][key_subject]['data']['done'] = round(consumptionhours[key_class]['data'][key_subject]['data']['done'], 2)
                consumptionhours[key_class]['data'][key_subject]['data']['awaiting'] = round(consumptionhours[key_class]['data'][key_subject]['data']['awaiting'], 2)

                consumptionhours[key_class]['hours_credit'] += consumptionhours[key_class]['data'][key_subject]['data']['credit']
                consumptionhours[key_class]['total_all'] += consumptionhours[key_class]['data'][key_subject]['data']['done']
                consumptionhours[key_class]['total_done'] += consumptionhours[key_class]['data'][key_subject]['data']['done']
                consumptionhours[key_class]['total_awaiting'] += consumptionhours[key_class]['data'][key_subject]['data']['awaiting']

        for key_class in consumptionhours.keys():
            consumptionhours[key_class]['hours_credit'] = round(consumptionhours[key_class]['hours_credit'], 2)
            consumptionhours[key_class]['total_all'] = round(consumptionhours[key_class]['total_all'], 2)
            consumptionhours[key_class]['total_done'] = round(consumptionhours[key_class]['total_done'], 2)
            consumptionhours[key_class]['total_awaiting'] = round(consumptionhours[key_class]['total_awaiting'], 2)

        _logger.info(f'----------- tototototototo consumptionhours {consumptionhours} -----------')

        return consumptionhours

    @staticmethod
    def format_progressreport(data):
        progressreports = {}

        sorted_data = copy.deepcopy(data)

        for d in sorted_data:
            key_class = '{}'.format(d['class_id'])
            key_subject = '{}'.format(d['subject_id'])
            if key_class not in progressreports:
                progressreports[key_class] = {}
                progressreports[key_class]['name'] = d['class_name']
                progressreports[key_class]['data'] = {}
                progressreports[key_class]['data'][key_subject] = {}
                progressreports[key_class]['data'][key_subject]['name'] = d['subject_name']
                progressreports[key_class]['data'][key_subject]['data'] = []
                progressreports[key_class]['data'][key_subject]['data'].append(d)
            else:
                if key_subject not in progressreports[key_class]['data']:
                    progressreports[key_class]['data'][key_subject] = {}
                    progressreports[key_class]['data'][key_subject]['name'] = d['subject_name']
                    progressreports[key_class]['data'][key_subject]['data'] = []
                    progressreports[key_class]['data'][key_subject]['data'].append(d)
                else:
                    progressreports[key_class]['data'][key_subject]['data'].append(d)

        for key_class in progressreports.keys():
            for key_subject in progressreports[key_class]['data'].keys():
                subjectsessions = Helpers.format_subjectsession(progressreports[key_class]['data'][key_subject]['data'])
                percentage_session = None
                for key_timetable in subjectsessions.keys():
                    if subjectsessions[key_timetable]['status'] == 'Effectué':
                        for d in subjectsessions[key_timetable]['data']:
                            if not percentage_session:
                                percentage_session = d['percentage']
                            else:
                                if d['percentage'] > percentage_session:
                                    percentage_session = d['percentage']

                if percentage_session:
                    progressreports[key_class]['data'][key_subject]['percentage'] = percentage_session
                else:
                    progressreports[key_class]['data'][key_subject]['percentage'] = 0.0

        _logger.info(f'----------- tototototototo progressreports {progressreports} -----------')

        return progressreports

    @staticmethod
    def format_examscore(data):
        examscores = {}

        sorted_data = copy.deepcopy(data)

        for d in sorted_data:
            key_class = '{}'.format(d['class_id'])
            key_semester = '{}'.format(d['semester_id'])
            key_student = '{}'.format(d['student_id'])
            key_subject = '{}'.format(d['subject_id'])
            if key_class not in examscores:
                examscores[key_class] = {}
                examscores[key_class]['name'] = d['class_name']
                examscores[key_class]['data'] = {}
                examscores[key_class]['data'][key_semester] = {}
                examscores[key_class]['data'][key_semester]['name'] = d['semester_name']
                examscores[key_class]['data'][key_semester]['data'] = {}
                examscores[key_class]['data'][key_semester]['data'][key_student] = {}
                examscores[key_class]['data'][key_semester]['data'][key_student]['name'] = d['student_name']
                examscores[key_class]['data'][key_semester]['data'][key_student]['data'] = {}
                examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject] = {}
                examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['name'] = d['subject_name']
                examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data'] = []
                examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data'].append(d)
            else:
                if key_semester not in examscores[key_class]['data']:
                    examscores[key_class]['data'][key_semester] = {}
                    examscores[key_class]['data'][key_semester]['name'] = d['semester_name']
                    examscores[key_class]['data'][key_semester]['data'] = {}
                    examscores[key_class]['data'][key_semester]['data'][key_student] = {}
                    examscores[key_class]['data'][key_semester]['data'][key_student]['name'] = d['student_name']
                    examscores[key_class]['data'][key_semester]['data'][key_student]['data'] = {}
                    examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject] = {}
                    examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['name'] = d['subject_name']
                    examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data'] = []
                    examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data'].append(d)
                else:
                    if key_student not in examscores[key_class]['data'][key_semester]['data']:
                        examscores[key_class]['data'][key_semester]['data'][key_student] = {}
                        examscores[key_class]['data'][key_semester]['data'][key_student]['name'] = d['student_name']
                        examscores[key_class]['data'][key_semester]['data'][key_student]['data'] = {}
                        examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject] = {}
                        examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['name'] = d['subject_name']
                        examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data'] = []
                        examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data'].append(d)
                    else:
                        if key_subject not in examscores[key_class]['data'][key_semester]['data'][key_student]['data']:
                            examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject] = {}
                            examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['name'] = d['subject_name']
                            examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data'] = []
                            examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data'].append(d)
                        else:
                            examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data'].append(d)

        _logger.info(f'----------- tototototototo examscores {examscores} -----------')

        return examscores

    @staticmethod
    def format_subjectsession(data):
        subjectsessions = {}

        sorted_data = copy.deepcopy(data)

        percentage_session = sum([len(d['sessions']) for d in sorted_data])
        if percentage_session > 0:
            percentage_session = (1 / percentage_session) * 100
        else:
            percentage_session = 0.0
        percentage_session = round(percentage_session, 2)

        total_session = 0.0
        for d in sorted_data:
            key_timetable = '{}'.format(d['id'])
            if key_timetable not in subjectsessions:
                subjectsessions[key_timetable] = {}
                subjectsessions[key_timetable]['id'] = d['id']
                subjectsessions[key_timetable]['name'] = d['name']
                subjectsessions[key_timetable]['status'] = 'Effectué' if d['status'] in ['present', 'permission'] else 'En attente'
                subjectsessions[key_timetable]['class_id'] = d['class_id']
                subjectsessions[key_timetable]['class_name'] = d['class_name']
                subjectsessions[key_timetable]['subject_id'] = d['subject_id']
                subjectsessions[key_timetable]['subject_name'] = d['subject_name']
                subjectsessions[key_timetable]['date'] = d['date_of_week']
                subjectsessions[key_timetable]['start_time'] = Helpers.convert_float_to_time(d['start_time'])
                subjectsessions[key_timetable]['end_time'] = Helpers.convert_float_to_time(d['end_time'])
                for v in d['sessions']:
                    total_session += percentage_session
                    total_session = round(total_session, 2)
                    v['percentage'] = total_session if total_session <= 100.0 else 100.0
                subjectsessions[key_timetable]['data'] = d['sessions']

        _logger.info(f'----------- tototototototo subjectsessions {subjectsessions} -----------')

        return subjectsessions

    @staticmethod
    def format_calendar(data, search_year):
        calendars = {}

        data.sort(key=lambda d: d['start'])
        sorted_data = copy.deepcopy(data)

        search_year = [str(y) for y in search_year]
        search_year = '-'.join(search_year)

        for d in sorted_data:
            _year, week, day = d['start'].isocalendar()
            month = d['start'].month
            date_today = date.today()
            month = str(month)
            if search_year not in calendars:
                calendars[search_year] = {}
                calendars[search_year][month] = {}
                calendars[search_year][month]['name'] = CURRENT_MONTH[month]
                calendars[search_year][month]['is_current_month'] = (str(date_today.year) in search_year and str(date_today.month) == month)
                if calendars[search_year][month]['is_current_month']:
                    calendars[search_year][month]['current_year'] = str(date_today.year)
                calendars[search_year][month]['data'] = []
                calendars[search_year][month]['data'].append(d)
            else:
                if month not in calendars[search_year]:
                    calendars[search_year][month] = {}
                    calendars[search_year][month]['name'] = CURRENT_MONTH[month]
                    calendars[search_year][month]['is_current_month'] = (str(date_today.year) in search_year and str(date_today.month) == month)
                    if calendars[search_year][month]['is_current_month']:
                        calendars[search_year][month]['current_year'] = str(date_today.year)
                    calendars[search_year][month]['data'] = []
                    calendars[search_year][month]['data'].append(d)
                else:
                    calendars[search_year][month]['data'].append(d)

        for year in calendars.keys():
            for month in calendars[year].keys():
                if not 'current_year' in calendars[year][month]:
                    calendars[year][month]['current_year'] = ''

        _logger.info(f'----------- tototototototo calendars {calendars} -----------')

        return calendars, search_year

    @staticmethod
    def convert_number_of_hours(tm):
        end_time = Helpers.convert_float_to_time(tm['end_time'], True)
        start_time = Helpers.convert_float_to_time(tm['start_time'], True)
        datetime_to = datetime.strptime(f"{tm['date']} {end_time}", DATETIME_FORMAT)
        datetime_from = datetime.strptime(f"{tm['date']} {start_time}", DATETIME_FORMAT)
        weekly_hours_credit = datetime_to - datetime_from
        weekly_hours_credit = weekly_hours_credit - timedelta(hours=tm['not_active_slotitems'])
        weekly_hours_credit = weekly_hours_credit.total_seconds() / 3600.0
        weekly_hours_credit = round(weekly_hours_credit, 2)
        return weekly_hours_credit

    @staticmethod
    def convert_datetime_from_utc(dt):
        new_tz = pytz.timezone('Africa/Douala')
        old_tz = pytz.utc
        local_dt = old_tz.localize(dt)
        dt = local_dt.astimezone(new_tz)
        return dt

    @staticmethod
    def convert_datetime_to_utc(dt):
        old_tz = pytz.timezone('Africa/Douala')
        new_tz = pytz.utc
        local_dt = old_tz.localize(dt)
        dt = local_dt.astimezone(new_tz)
        return dt

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
        tm = Helpers.convert_time_to_float(tm)
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
    def paginate_list(items, page_size=10, page_number=1):
        if page_size == 0:
            page_size = 10
        pages_total = [items[i:i+page_size] for i in range(0, len(items), page_size)]
        start_index = (page_number - 1) * page_size
        end_index = start_index + page_size
        pages = items[start_index:end_index]
        return {
            'total': len(items),
            'pages_total': len(pages_total),
            'pages': pages,
        }

    @staticmethod
    def serialize_datetime(obj):
        if isinstance(obj, date):
            return datetime.strftime(obj, DATE_FORMAT_FR)
        elif isinstance(obj, datetime):
            return datetime.strftime(obj, DATETIME_FORMAT_FR)
        elif isinstance(obj, time):
            return datetime.strftime(obj, TIME_FORMAT_FR)
        else:
            return obj
