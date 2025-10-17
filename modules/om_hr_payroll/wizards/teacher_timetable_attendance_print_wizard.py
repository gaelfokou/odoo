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

class TimetablePrintWizard(models.TransientModel):
    _name = 'timetable.print.wizard'
    _description = 'Assistant d\'impression des emplois du temps'

    # Enseignant lié à la programmation de cours
    employee_id = fields.Many2one(
        'hr.employee',
        'Enseignant',
    )

    start_date = fields.Date(
        'Date de début',
    )

    end_date = fields.Date(
        'Date de fin',
    )

    status = fields.Selection([
        ('pending', 'En attente'),
        ('progress', 'En cours'),
        ('present', 'Présent'),
        ('absent', 'Absent'),
        ('permission', 'Permission'),
        ('exception', 'Exception'),
        ('delay', 'Retard'),
    ], 'Statut',
        default='present',
    )

    # Contrainte logique pour s'assurer que les dates de début et de fin sont définies et que la date de fin est supérieure à la date de début
    @api.constrains('start_date', 'end_date')
    def _constrains_date(self):
        for record in self:
            if record.end_date < record.start_date:
                raise ValidationError("La date de fin doit être supérieure à la date de début")

    def action_print_pdf(self):
        data = self.print_teacher_timetable_attendance_report_data()

        # Appeler le rapport PDF
        if not data['docdata']['timetable_data']:
            raise UserError("Aucune donnée trouvée")
        report_action = self.env.ref('siantou_ems_core.action_report_timetable')
        return report_action.report_action(self, data=data)

    def print_teacher_timetable_attendance_report_data(self):
        # Récupérer les emplois du temps pour le semestre sélectionné
        domain = []

        search_teacher_timetable_attendances = self.env['teacher.timetable.attendance'].search(domain)

        teacher_timetable_attendances = {}
        info_teacher_timetable_attendances = {}
        for search_teacher_timetable_attendance in search_teacher_timetable_attendances:
            key = '{}-{}-{}-{}'.format(search_teacher_timetable_attendance.semester_id.id, search_teacher_timetable_attendance.class_id.id, search_teacher_timetable_attendance.field_of_study_id.id, search_teacher_timetable_attendance.specialty_id.id, search_teacher_timetable_attendance.level_id.id, search_teacher_timetable_attendance.batch_id.id)
            semester = '{}'.format(search_teacher_timetable_attendance.semester_id.name)
            study = '{} - {} - {} - {}'.format(search_teacher_timetable_attendance.class_id.name, search_teacher_timetable_attendance.field_of_study_id.name, search_teacher_timetable_attendance.specialty_id.name if search_teacher_timetable_attendance.specialty_id.id else '', search_teacher_timetable_attendance.level_id.name, search_teacher_timetable_attendance.batch_id.name)
            if not key in teacher_timetable_attendances:
                teacher_timetable_attendances[key] = []
                info_teacher_timetable_attendances[key] = {}
                info_teacher_timetable_attendances[key]['semester'] = semester
                info_teacher_timetable_attendances[key]['study'] = study
                info_teacher_timetable_attendances[key]['filter'] = self.env['ir.config_parameter'].sudo().get_param(f'siantou.filter_user_{self.env.user.id}', '')
            teacher_timetable_attendance = {}
            teacher_timetable_attendance['id'] = search_teacher_timetable_attendance.id
            teacher_timetable_attendance['date'] = search_teacher_timetable_attendance.date
            teacher_timetable_attendance['date_of_week'] = datetime.strftime(search_teacher_timetable_attendance.date, DATE_FORMAT_FR)
            teacher_timetable_attendance['semester_name'] = search_teacher_timetable_attendance.semester_id.name
            teacher_timetable_attendance['cycle_id'] = search_teacher_timetable_attendance.cycle_id.id
            teacher_timetable_attendance['cycle_name'] = search_teacher_timetable_attendance.cycle_id.name
            teacher_timetable_attendance['level_id'] = search_teacher_timetable_attendance.level_id.id
            teacher_timetable_attendance['level_name'] = search_teacher_timetable_attendance.level_id.name
            teacher_timetable_attendance['field_of_study_id'] = search_teacher_timetable_attendance.field_of_study_id.id
            teacher_timetable_attendance['field_of_study_name'] = search_teacher_timetable_attendance.field_of_study_id.name
            teacher_timetable_attendance['specialty_id'] = search_teacher_timetable_attendance.specialty_id.id
            teacher_timetable_attendance['specialty_name'] = search_teacher_timetable_attendance.specialty_id.name
            teacher_timetable_attendance['option_id'] = search_teacher_timetable_attendance.option_id.id
            teacher_timetable_attendance['option_name'] = search_teacher_timetable_attendance.option_id.name
            teacher_timetable_attendance['class_id'] = search_teacher_timetable_attendance.class_id.id
            teacher_timetable_attendance['class_name'] = search_teacher_timetable_attendance.class_id.name
            teacher_timetable_attendance['department_id'] = search_teacher_timetable_attendance.department_id.id
            teacher_timetable_attendance['department_name'] = search_teacher_timetable_attendance.department_id.name
            teacher_timetable_attendance['school_id'] = search_teacher_timetable_attendance.school_id.id
            teacher_timetable_attendance['school_name'] = search_teacher_timetable_attendance.school_id.name
            teacher_timetable_attendance['subject_id'] = search_teacher_timetable_attendance.subject_id.id
            teacher_timetable_attendance['subject_name'] = search_teacher_timetable_attendance.subject_id.name
            teacher_timetable_attendance['subject_code'] = search_teacher_timetable_attendance.subject_id.code
            teacher_timetable_attendance['subject_shared_subject'] = '(TC)' if search_teacher_timetable_attendance.subject_id.shared_subject else ''
            teacher_timetable_attendance['classroom_name'] = search_teacher_timetable_attendance.classroom_id.name
            teacher_timetable_attendance['building_name'] = search_teacher_timetable_attendance.classroom_id.building_id.name
            teacher_timetable_attendance['batch_name'] = search_teacher_timetable_attendance.batch_id.name
            teacher_timetable_attendance['employee_name'] = search_teacher_timetable_attendance.employee_id.name
            teacher_timetable_attendance['day_of_week'] = CURRENT_WEEKDAY[search_teacher_timetable_attendance.day_of_week]
            teacher_timetable_attendance['start_time'] = search_teacher_timetable_attendance.start_time
            teacher_timetable_attendance['end_time'] = search_teacher_timetable_attendance.end_time
            teacher_timetable_attendance['not_active_slotitems'] = search_teacher_timetable_attendance.not_active_slotitems
            teacher_timetable_attendance['status'] = STATUS_TIMETABLE[search_teacher_timetable_attendance.status]
            teacher_timetable_attendances[key].append(teacher_timetable_attendance)

        for key in teacher_timetable_attendances.keys():
            if len(teacher_timetable_attendances[key]) > 0:
                field_of_study_id = teacher_timetable_attendances[key][0]['field_of_study_id']

                slots = self.env['siantou.ems.timetable.slot'].search([
                    ('is_active', '=', False),
                ])
                slots = list(slots)

                available_slotitem = None
                for slot in slots:
                    field_of_study_ids = list(slot.field_of_study_ids)
                    for field_of_study in field_of_study_ids:
                        if field_of_study.id == field_of_study_id:
                            available_slotitem = slot
                            break
                    if available_slotitem:
                        break

                if available_slotitem:
                    slots = self.env['siantou.ems.timetable.slot'].search([
                        ('id', '=', available_slotitem.id),
                    ])
                else:
                    slots = self.env['siantou.ems.timetable.slot'].search([
                        ('is_active', '=', True),
                    ])

                slots = list(slots)

                not_active_slotitems = []
                for slot in slots:
                    not_active_slotitem_day_ids = slot.slotitem_day_ids.filtered(lambda s: not s.is_active)
                    not_active_slotitem_day_ids = list(not_active_slotitem_day_ids)
                    for not_active_slotitem_day_id in not_active_slotitem_day_ids:
                        not_active_slotitems.append([round(not_active_slotitem_day_id.start_time, 2), round(not_active_slotitem_day_id.end_time, 2)])
                    not_active_slotitem_night_ids = slot.slotitem_night_ids.filtered(lambda s: not s.is_active)
                    not_active_slotitem_night_ids = list(not_active_slotitem_night_ids)
                    for not_active_slotitem_night_id in not_active_slotitem_night_ids:
                        not_active_slotitems.append([round(not_active_slotitem_night_id.start_time, 2), round(not_active_slotitem_night_id.end_time, 2)])

                teacher_timetable_attendances[key] = TimetablePrintWizard.format_timetable(teacher_timetable_attendances[key], not_active_slotitems)
            else:
                teacher_timetable_attendances[key] = TimetablePrintWizard.format_timetable(teacher_timetable_attendances[key])
            for monday in teacher_timetable_attendances[key].keys():
                for i, timetable in enumerate(teacher_timetable_attendances[key][monday]['Heure']):
                    tm = timetable.split('-')
                    tm[0] = TimetablePrintWizard.convert_float_to_time(tm[0])
                    tm[1] = TimetablePrintWizard.convert_float_to_time(tm[1])
                    teacher_timetable_attendances[key][monday]['Heure'][i] = '{}-{}'.format(tm[0], tm[1])
            teacher_timetable_attendances[key] = TimetablePrintWizard.paginate_calendar(teacher_timetable_attendances[key], len(teacher_timetable_attendances[key].keys()))
            teacher_timetable_attendances[key]['semester'] = info_teacher_timetable_attendances[key]['semester']
            teacher_timetable_attendances[key]['study'] = info_teacher_timetable_attendances[key]['study']
            teacher_timetable_attendances[key]['filter'] = info_teacher_timetable_attendances[key]['filter']

        _logger.info(f'----------- tototototototo teacher_timetable_attendances {teacher_timetable_attendances} -----------')

        return {
            'docdata': {
                'timetable_data': teacher_timetable_attendances,
                'semester': self.semester_id.name,
            }
        }

    @staticmethod
    def convert_float_to_time(tm, has_second=False):
        tm = str(tm)
        tm = tm.split('.')
        if len(tm[0]) == 1:
            tm[0] = '0{}'.format(tm[0])
        if len(tm[1]) == 1:
            tm[1] = '{}0'.format(tm[1])
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
