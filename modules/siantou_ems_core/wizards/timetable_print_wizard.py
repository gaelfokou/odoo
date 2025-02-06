import logging

from odoo import models, fields, api
from odoo.exceptions import UserError
from pprint import pformat
import pandas as pd
import numpy as np
import re
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import copy

DATE_FORMAT = '%Y-%m-%d'
DATE_FORMAT_FR = '%d/%m/%Y'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATETIME_FORMAT_FR = '%d/%m/%Y %H:%M'
TIME_FORMAT = '%H:%M'

CURRENT_WEEKDAY = {
    0: 'Lundi',
    1: 'Mardi',
    2: 'Mercredi',
    3: 'Jeudi',
    4: 'Vendredi',
    5: 'Samedi',
    6: 'Dimanche',
}

STATUS_TIMETABLE = {
    '0': 'En attente',
    '1': 'Présent',
    '2': 'Absent',
    '3': 'Permissionnaire',
    '4': 'Exception',
}

_logger = logging.getLogger(__name__)
class TimetablePrintWizard(models.TransientModel):
    _name = 'siantou.ems.timetable.timetable_print_wizard'
    _description = 'Assistant d\'impression de l\'emploi du temps'

    # Semestre pour lequel on souhaite tirer l'emploi du temps
    semester_id = fields.Many2one(
        'siantou.ems.core.year.semester',
        'Semester',
        required=True
    )

    # Niveau lié à la programmation de cours
    level_id = fields.Many2one(
        'siantou.ems.core.level',
        'Niveau',
        ondelete='restrict'
    )

    # Ajouter un champ de relation vers hr.department pour lier la filière au département
    department_id = fields.Many2one(
        'hr.department',
        string='Département'
    )

    # Filière liée à la programmation de cours
    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        'Filière',
        ondelete='restrict'
    )

    # Période de début
    period_from = fields.Date(
        'Période de',
    )

    # Période de fin
    period_to = fields.Date(
        'Période à',
    )

    group_id = fields.Many2one(
        'siantou.ems.timetable.group',
        'Version',
        required=True
    )

    def print_timetable(self):
        data = self.print_timetable_report_data()

        # Appeler le rapport PDF
        if not data['docdata']['timetable_data']:
            raise UserError("Aucune donnée trouvée.")
        report_action = self.env.ref('siantou_ems_core.action_report_timetable')
        return report_action.report_action(self, data=data)

    def print_timetable_report_data(self, domains=None):
        # Récupérer les emplois du temps pour le semestre sélectionné
        domain = [
            ('semester_id', '=', self.semester_id.id),
            ('group_id', '=', self.group_id.id)
        ]
        # Ajouter le critère Niveau seulement s'il est sélectionné
        if self.level_id:
            domain.append(('level_id', '=', self.level_id.id))

        # Ajouter le critère Filière seulement s'il est sélectionné
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        
        # Ajouter le critère Filière seulement s'il est sélectionné
        if self.field_of_study_id:
            domain.append(('field_of_study_id', '=', self.field_of_study_id.id))
        
        # Ajouter le critère de période seulement si la période de début et la période de fin sont sélectionnées
        if self.period_from and self.period_to:
            domain.append(('date', '>=', self.period_from))
            domain.append(('date', '<=', self.period_to))

        if domains:
            domain = [
                ('semester_id', '=', self.semester_id.id),
                ('group_id', '=', self.group_id.id)
            ]
            for d in domains:
                domain.append(d)

        search_timetables = self.env['siantou.ems.timetable.timetable'].search(domain)

        timetables = {}
        info_timetables = {}
        for search_timetable in search_timetables:
            key = '{}-{}-{}-{}'.format(search_timetable.semester_id.id, search_timetable.field_of_study_id.id, search_timetable.level_id.id, search_timetable.batch_id.id)
            semester = '{}'.format(search_timetable.semester_id.name)
            study = '{} - {} - {}'.format(search_timetable.field_of_study_id.name, search_timetable.level_id.name, search_timetable.batch_id.name)
            if not key in timetables:
                timetables[key] = []
                info_timetables[key] = {}
                info_timetables[key]['semester'] = semester
                info_timetables[key]['study'] = study
            timetable = {}
            timetable['id'] = search_timetable.id
            timetable['date'] = search_timetable.date
            timetable['date_of_week'] = datetime.strftime(search_timetable.date, DATE_FORMAT_FR)
            timetable['field_of_study_id'] = search_timetable.field_of_study_id.id
            timetable['field_of_study_name'] = search_timetable.field_of_study_id.name
            timetable['semester_name'] = search_timetable.semester_id.name
            timetable['level_name'] = search_timetable.level_id.name
            timetable['department_id'] = search_timetable.department_id.id
            timetable['department_name'] = search_timetable.department_id.name
            timetable['subject_name'] = search_timetable.subject_id.name
            timetable['subject_code'] = search_timetable.subject_id.code
            timetable['classroom_name'] = search_timetable.classroom_id.name
            timetable['building_name'] = search_timetable.classroom_id.building_id.name
            timetable['batch_name'] = search_timetable.batch_id.name
            timetable['employee_name'] = search_timetable.employee_id.name
            timetable['day_of_week'] = CURRENT_WEEKDAY[search_timetable.date.weekday()]
            timetable['start_time'] = search_timetable.start_time
            timetable['end_time'] = search_timetable.end_time
            timetable['status'] = STATUS_TIMETABLE[search_timetable.status]
            timetables[key].append(timetable)

        for key in timetables.keys():
            if len(timetables[key]) > 0:
                field_of_study_id = timetables[key][0]['field_of_study_id']

                slots = self.env['siantou.ems.timetable.slot'].search([
                    ('is_default', '=', False),
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
                        ('is_default', '=', True),
                    ])

                slots = list(slots)

                slotitems = []
                for slot in slots:
                    slotitem_day_ids = slot.slotitem_day_ids.filtered(lambda s: not s.is_active)
                    slotitem_day_ids = list(slotitem_day_ids)
                    for slotitem_day_id in slotitem_day_ids:
                        slotitems.append([round(slotitem_day_id.start_time, 2), round(slotitem_day_id.end_time, 2)])
                    slotitem_night_ids = slot.slotitem_night_ids.filtered(lambda s: not s.is_active)
                    slotitem_night_ids = list(slotitem_night_ids)
                    for slotitem_night_id in slotitem_night_ids:
                        slotitems.append([round(slotitem_night_id.start_time, 2), round(slotitem_night_id.end_time, 2)])

                timetables[key] = TimetablePrintWizard.format_timetable(timetables[key], slotitems)
            else:
                timetables[key] = TimetablePrintWizard.format_timetable(timetables[key])
            for monday in timetables[key].keys():
                for i, timetable in enumerate(timetables[key][monday]['Heure']):
                    tm = timetable.split('-')
                    tm[0] = TimetablePrintWizard.convert_float_to_time(tm[0])
                    tm[1] = TimetablePrintWizard.convert_float_to_time(tm[1])
                    timetables[key][monday]['Heure'][i] = '{}-{}'.format(tm[0], tm[1])
            timetables[key] = TimetablePrintWizard.paginate_calendar(timetables[key], len(timetables[key].keys()))
            timetables[key]['semester'] = info_timetables[key]['semester']
            timetables[key]['study'] = info_timetables[key]['study']

        _logger.info(f'----------- tototototototo timetables {timetables} -----------')

        return {
            'docdata': {
                'timetable_data': timetables,
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
        tm = datetime.combine(date.today(), tm) + timedelta(hours=int(n[0]), minutes=int(n[1]))
        tm = datetime.strftime(tm, TIME_FORMAT)
        tm = TimetablePrintWizard.convert_time_to_float(tm)
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
    def format_timetable(data, hours=[]):
        n = 0.0
        current_data = []
        current_hours = []
        timetables = {}
        df = {}

        for i in range(len(data)):
            data[i]['start_time'] = round(data[i]['start_time'], 2)
            data[i]['end_time'] = round(data[i]['end_time'], 2)
            h = [hour for hour in hours if (TimetablePrintWizard.increment_float_time(data[i]['start_time']) <= TimetablePrintWizard.increment_float_time(hour[0]) and TimetablePrintWizard.increment_float_time(data[i]['end_time']) > TimetablePrintWizard.increment_float_time(hour[0])) or (TimetablePrintWizard.increment_float_time(data[i]['start_time']) < TimetablePrintWizard.increment_float_time(hour[1]) and TimetablePrintWizard.increment_float_time(data[i]['end_time']) >= TimetablePrintWizard.increment_float_time(hour[1]))]
            if len(h) == 0:
                current_data.append(data[i])
            else:
                h = [hour for hour in hours if TimetablePrintWizard.increment_float_time(data[i]['start_time']) == TimetablePrintWizard.increment_float_time(hour[0]) and TimetablePrintWizard.increment_float_time(data[i]['end_time']) == TimetablePrintWizard.increment_float_time(hour[1])]
                if len(h) == 0:
                    h = [hour for hour in hours if TimetablePrintWizard.increment_float_time(data[i]['start_time']) < TimetablePrintWizard.increment_float_time(hour[0]) and TimetablePrintWizard.increment_float_time(data[i]['end_time']) > TimetablePrintWizard.increment_float_time(hour[1])]
                    if len(h) == 0:
                        h = [hour for hour in hours if TimetablePrintWizard.increment_float_time(data[i]['start_time']) == TimetablePrintWizard.increment_float_time(hour[0])]
                        if len(h) > 0:
                            data[i]['start_time'] = h[0][1]
                            current_data.append(data[i])
                        else:
                            h = [hour for hour in hours if TimetablePrintWizard.increment_float_time(data[i]['end_time']) == TimetablePrintWizard.increment_float_time(hour[1])]
                            if len(h) > 0:
                                data[i]['end_time'] = h[0][0]
                                current_data.append(data[i])
                    else:
                        data1 = copy.deepcopy(data[i])
                        data2 = copy.deepcopy(data[i])
                        data1['end_time'] = h[0][0]
                        data2['start_time'] = h[0][1]
                        current_data.append(data1)
                        current_data.append(data2)

        data = current_data
        data.sort(key=lambda d: d['date'])
        sorted_data = copy.deepcopy(data)

        for i, d in enumerate(data):
            if i == 0:
                n = d['end_time'] - d['start_time']
            else:
                if n > d['end_time'] - d['start_time']:
                    n = d['end_time'] - d['start_time']
            hours.append([d['start_time'], d['end_time']])

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
                                        if np.isnan(float(str(df[monday].loc[i, column]))):
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

    def convert_number_to_weekday(self, number):
        if number == '0':
            return "Lundi"
        if number == '1':
            return "Mardi"
        if number == '2':
            return "Mercredi"
        if number == '3':
            return "Jeudi"
        if number == '4':
            return "Vendredi"
        if number == '5':
            return "Samedi"

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