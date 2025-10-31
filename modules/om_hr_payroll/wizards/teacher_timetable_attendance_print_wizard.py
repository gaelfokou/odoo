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

class TeacherTimetableAttendancePrintWizard(models.TransientModel):
    _name = 'teacher.timetable.attendance.print.wizard'
    _description = 'Assistant d\'impression des émargements des enseignants'

    def action_print_pdf(self):
        data = self.print_teacher_timetable_attendance_report_data()

        # Appeler le rapport PDF
        if not data['docdata']['teacher_timetable_attendance_data']:
            raise UserError("Aucune donnée trouvée")
        report_action = self.env.ref('om_hr_payroll.action_report_teacher_timetable_attendance')
        return report_action.report_action(self, data=data)

    def print_teacher_timetable_attendance_report_data(self, domains=None):
        # Récupérer les emplois du temps pour le semestre sélectionné
        domain = []

        if domains:
            for d in domains:
                domain.append(d)

        search_teacher_timetable_attendances = self.env['teacher.timetable.attendance'].search(domain)

        is_permanent = False
        key_teacher_timetable_attendances = {}
        for search_teacher_timetable_attendance in search_teacher_timetable_attendances:
            if not search_teacher_timetable_attendance.date:
                continue
            key = '{}'.format(search_teacher_timetable_attendance.employee_id.id)
            if not key in key_teacher_timetable_attendances:
                key_teacher_timetable_attendances[key] = {}
                key_teacher_timetable_attendances[key]['name'] = search_teacher_timetable_attendance.employee_id.name
                key_teacher_timetable_attendances[key]['data'] = []
                key_teacher_timetable_attendances[key]['worked_time'] = 0.0
                key_teacher_timetable_attendances[key]['amount'] = 0.0
                key_teacher_timetable_attendances[key]['has_ir'] = None
                key_teacher_timetable_attendances[key]['has_apecus'] = None
                key_teacher_timetable_attendances[key]['has_cnps'] = None
                key_teacher_timetable_attendances[key]['has_allowance_cd'] = None
                key_teacher_timetable_attendances[key]['has_allowance_co'] = None
            is_permanent = search_teacher_timetable_attendance.employee_id.is_permanent
            teacher_timetable_attendance = {}
            teacher_timetable_attendance['id'] = search_teacher_timetable_attendance.id
            teacher_timetable_attendance['date'] = search_teacher_timetable_attendance.date
            teacher_timetable_attendance['date_of_week'] = datetime.strftime(search_teacher_timetable_attendance.date, DATE_FORMAT_FR)
            teacher_timetable_attendance['class_id'] = search_teacher_timetable_attendance.class_id.id
            teacher_timetable_attendance['class_name'] = search_teacher_timetable_attendance.class_id.name
            teacher_timetable_attendance['subject_id'] = search_teacher_timetable_attendance.subject_id.id
            teacher_timetable_attendance['subject_name'] = search_teacher_timetable_attendance.subject_id.name
            teacher_timetable_attendance['subject_code'] = search_teacher_timetable_attendance.subject_id.code
            teacher_timetable_attendance['subject_shared_subject'] = '(TC)' if search_teacher_timetable_attendance.subject_id.shared_subject else ''
            teacher_timetable_attendance['employee_name'] = search_teacher_timetable_attendance.employee_id.name
            teacher_timetable_attendance['start_time'] = TeacherTimetableAttendancePrintWizard.convert_float_to_time(search_teacher_timetable_attendance.start_time)
            teacher_timetable_attendance['end_time'] = TeacherTimetableAttendancePrintWizard.convert_float_to_time(search_teacher_timetable_attendance.end_time)
            teacher_timetable_attendance['worked_start_time'] = TeacherTimetableAttendancePrintWizard.convert_float_to_time(search_teacher_timetable_attendance.worked_start_time)
            teacher_timetable_attendance['worked_end_time'] = TeacherTimetableAttendancePrintWizard.convert_float_to_time(search_teacher_timetable_attendance.worked_end_time)
            teacher_timetable_attendance['worked_time'] = search_teacher_timetable_attendance.worked_time
            teacher_timetable_attendance['rate'] = search_teacher_timetable_attendance.rate
            teacher_timetable_attendance['amount'] = search_teacher_timetable_attendance.amount
            teacher_timetable_attendance['hours_credit'] = search_teacher_timetable_attendance.hours_credit
            teacher_timetable_attendance['total_all'] = search_teacher_timetable_attendance.total_all
            teacher_timetable_attendance['total_done'] = search_teacher_timetable_attendance.total_done
            teacher_timetable_attendance['total_awaiting'] = search_teacher_timetable_attendance.total_awaiting
            teacher_timetable_attendance['status'] = STATUS_TIMETABLE[search_teacher_timetable_attendance.status]
            key_teacher_timetable_attendances[key]['has_ir'] = search_teacher_timetable_attendance.employee_id.has_ir
            key_teacher_timetable_attendances[key]['has_apecus'] = search_teacher_timetable_attendance.employee_id.has_apecus
            key_teacher_timetable_attendances[key]['has_cnps'] = search_teacher_timetable_attendance.employee_id.has_cnps
            key_teacher_timetable_attendances[key]['has_allowance_cd'] = search_teacher_timetable_attendance.employee_id.has_allowance_cd
            key_teacher_timetable_attendances[key]['has_allowance_co'] = search_teacher_timetable_attendance.employee_id.has_allowance_co
            key_teacher_timetable_attendances[key]['worked_time'] += teacher_timetable_attendance['worked_time']
            key_teacher_timetable_attendances[key]['amount'] += teacher_timetable_attendance['amount']
            key_teacher_timetable_attendances[key]['worked_time'] = round(key_teacher_timetable_attendances[key]['worked_time'], 2)
            key_teacher_timetable_attendances[key]['amount'] = round(key_teacher_timetable_attendances[key]['amount'], 2)
            key_teacher_timetable_attendances[key]['data'].append(teacher_timetable_attendance)

        for key in key_teacher_timetable_attendances.keys():
            if key_teacher_timetable_attendances[key]['has_allowance_cd']:
                employee_salary_allowance = self.env['employee.salary.allowance'].sudo().search([('allowance_type', '=', 'cd')], limit=1)
                if employee_salary_allowance:
                    teacher_timetable_attendance = {}
                    teacher_timetable_attendance['date_of_week'] = ''
                    teacher_timetable_attendance['class_name'] = ''
                    teacher_timetable_attendance['subject_name'] = employee_salary_allowance.name
                    teacher_timetable_attendance['employee_name'] = ''
                    teacher_timetable_attendance['start_time'] = ''
                    teacher_timetable_attendance['end_time'] = ''
                    teacher_timetable_attendance['worked_start_time'] = ''
                    teacher_timetable_attendance['worked_end_time'] = ''
                    teacher_timetable_attendance['worked_time'] = ''
                    teacher_timetable_attendance['rate'] = ''
                    teacher_timetable_attendance['amount'] = employee_salary_allowance.amount
                    teacher_timetable_attendance['hours_credit'] = ''
                    teacher_timetable_attendance['total_all'] = ''
                    teacher_timetable_attendance['total_done'] = ''
                    teacher_timetable_attendance['total_awaiting'] = ''
                    key_teacher_timetable_attendances[key]['amount'] += teacher_timetable_attendance['amount']
                    key_teacher_timetable_attendances[key]['data'].append(teacher_timetable_attendance)
            if key_teacher_timetable_attendances[key]['has_allowance_co']:
                employee_salary_allowance = self.env['employee.salary.allowance'].sudo().search([('allowance_type', '=', 'co')], limit=1)
                if employee_salary_allowance:
                    teacher_timetable_attendance = {}
                    teacher_timetable_attendance['date_of_week'] = ''
                    teacher_timetable_attendance['class_name'] = ''
                    teacher_timetable_attendance['subject_name'] = employee_salary_allowance.name
                    teacher_timetable_attendance['employee_name'] = ''
                    teacher_timetable_attendance['start_time'] = ''
                    teacher_timetable_attendance['end_time'] = ''
                    teacher_timetable_attendance['worked_start_time'] = ''
                    teacher_timetable_attendance['worked_end_time'] = ''
                    teacher_timetable_attendance['worked_time'] = ''
                    teacher_timetable_attendance['rate'] = ''
                    teacher_timetable_attendance['amount'] = employee_salary_allowance.amount
                    teacher_timetable_attendance['hours_credit'] = ''
                    teacher_timetable_attendance['total_all'] = ''
                    teacher_timetable_attendance['total_done'] = ''
                    teacher_timetable_attendance['total_awaiting'] = ''
                    key_teacher_timetable_attendances[key]['amount'] += teacher_timetable_attendance['amount']
                    key_teacher_timetable_attendances[key]['data'].append(teacher_timetable_attendance)

            if key_teacher_timetable_attendances[key]['has_ir']:
                employee_salary_deduction = self.env['employee.salary.deduction'].sudo().search([('deduction_type', '=', 'ir')], limit=1)
                if employee_salary_deduction:
                    teacher_timetable_attendance = {}
                    teacher_timetable_attendance['date_of_week'] = ''
                    teacher_timetable_attendance['class_name'] = ''
                    teacher_timetable_attendance['subject_name'] = employee_salary_deduction.name
                    teacher_timetable_attendance['employee_name'] = ''
                    teacher_timetable_attendance['start_time'] = ''
                    teacher_timetable_attendance['end_time'] = ''
                    teacher_timetable_attendance['worked_start_time'] = ''
                    teacher_timetable_attendance['worked_end_time'] = ''
                    teacher_timetable_attendance['worked_time'] = ''
                    teacher_timetable_attendance['rate'] = ''
                    teacher_timetable_attendance['amount'] = employee_salary_deduction.amount
                    teacher_timetable_attendance['hours_credit'] = ''
                    teacher_timetable_attendance['total_all'] = ''
                    teacher_timetable_attendance['total_done'] = ''
                    teacher_timetable_attendance['total_awaiting'] = ''
                    key_teacher_timetable_attendances[key]['amount'] += teacher_timetable_attendance['amount']
                    key_teacher_timetable_attendances[key]['data'].append(teacher_timetable_attendance)

        title = self.env['ir.config_parameter'].sudo().get_param(f'siantou.filter_user_{self.env.user.id}', '')

        _logger.info(f'----------- tototototototo key_teacher_timetable_attendances {key_teacher_timetable_attendances} -----------')

        return {
            'docdata': {
                'filter': title,
                'teacher_timetable_attendance_data': key_teacher_timetable_attendances,
                'is_permanent': is_permanent,
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
        if len(tm[1]) == 1:
            tm[1] = '{}0'.format(tm[1])
        tm = time(int(tm[0]), int(tm[1]))
        n = str(n)
        n = n.split('.')
        if len(n[1]) == 1:
            n[1] = '{}0'.format(n[1])
        tm = datetime.combine(date.min, tm) + timedelta(hours=int(n[0]), minutes=int(n[1]))
        tm = datetime.strftime(tm, TIME_FORMAT_FR)
        tm = TimetablePrintWizard.convert_time_to_float(tm)
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
                    if not (TimetablePrintWizard.increment_float_time(data[i]['start_time']) <= TimetablePrintWizard.increment_float_time(hour[0]) and TimetablePrintWizard.increment_float_time(data[i]['end_time']) > TimetablePrintWizard.increment_float_time(hour[0])) or not (TimetablePrintWizard.increment_float_time(data[i]['start_time']) < TimetablePrintWizard.increment_float_time(hour[1]) and TimetablePrintWizard.increment_float_time(data[i]['end_time']) >= TimetablePrintWizard.increment_float_time(hour[1])):
                        current_data.append(data[i])
                        break
                    else:
                        if not (TimetablePrintWizard.increment_float_time(data[i]['start_time']) == TimetablePrintWizard.increment_float_time(hour[0]) and TimetablePrintWizard.increment_float_time(data[i]['end_time']) == TimetablePrintWizard.increment_float_time(hour[1])):
                            if not (TimetablePrintWizard.increment_float_time(data[i]['start_time']) < TimetablePrintWizard.increment_float_time(hour[0]) and TimetablePrintWizard.increment_float_time(data[i]['end_time']) > TimetablePrintWizard.increment_float_time(hour[1])):
                                if TimetablePrintWizard.increment_float_time(data[i]['start_time']) == TimetablePrintWizard.increment_float_time(hour[0]):
                                    data[i]['start_time'] = hour[1]
                                    current_data.append(data[i])
                                    break
                                else:
                                    if TimetablePrintWizard.increment_float_time(data[i]['end_time']) == TimetablePrintWizard.increment_float_time(hour[1]):
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
            while TimetablePrintWizard.increment_float_time(hours[i][0]) < TimetablePrintWizard.increment_float_time(hours[i][1]):
                if TimetablePrintWizard.increment_float_time(hours[i][0], n) < TimetablePrintWizard.increment_float_time(hours[i][1]):
                    h = '{}-{}'.format(TimetablePrintWizard.increment_float_time(hours[i][0]), TimetablePrintWizard.increment_float_time(hours[i][0], n))
                else:
                    h = '{}-{}'.format(TimetablePrintWizard.increment_float_time(hours[i][0]), TimetablePrintWizard.increment_float_time(hours[i][1]))
                current_hours.append(h)
                hours[i][0] = TimetablePrintWizard.increment_float_time(hours[i][0], n)

        current_hours = list(set(current_hours))
        current_hours.sort(key=lambda h: float(h.split('-')[0]))

        for d in sorted_data:
            if d['date'].weekday() == 0:
                monday = d['date']
            else:
                monday = d['date'] - timedelta(days=d['date'].weekday())
            monday = datetime.strftime(monday, DATE_FORMAT)
            if not monday in timetables:
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
            if not monday in df:
                df[monday] = pd.DataFrame(timetables[monday], dtype=str)
            while TimetablePrintWizard.increment_float_time(d['start_time']) < TimetablePrintWizard.increment_float_time(d['end_time']):
                if TimetablePrintWizard.increment_float_time(d['start_time'], n) < TimetablePrintWizard.increment_float_time(d['end_time']):
                    h = '{}-{}'.format(TimetablePrintWizard.increment_float_time(d['start_time']), TimetablePrintWizard.increment_float_time(d['start_time'], n))
                else:
                    h = '{}-{}'.format(TimetablePrintWizard.increment_float_time(d['start_time']), TimetablePrintWizard.increment_float_time(d['end_time']))
                for i, row in df[monday].iterrows():
                    if h == timetables[monday]['Heure'][i]:
                        for j, column in enumerate(df[monday].columns):
                            for k, key in enumerate(timetables[monday].keys()):
                                if k == d['date'].weekday() + 1:
                                    if column == key:
                                        if TimetablePrintWizard.is_float(str(df[monday].loc[i, column])) and np.isnan(float(str(df[monday].loc[i, column]))):
                                            df[monday].loc[i, column] = str(d['id'])
                                        else:
                                            df[monday].loc[i, column] = '{}-{}'.format(df[monday].loc[i, column], str(d['id']))
                                    break
                d['start_time'] = TimetablePrintWizard.increment_float_time(d['start_time'], n)

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
