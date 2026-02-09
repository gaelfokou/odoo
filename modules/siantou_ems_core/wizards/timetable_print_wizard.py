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

    def action_print_pdf(self):
        data = self.print_timetable_report_data()

        # Appeler le rapport PDF
        if len(data['docdata']['timetable_data']) == 0:
            raise UserError("Aucune donnée trouvée")
        report_action = self.env.ref('siantou_ems_core.action_report_timetable')
        return report_action.report_action(self, data=data)

    def print_timetable_report_data(self, domains=None):
        # Récupérer les emplois du temps pour le semestre sélectionné
        domain = []

        if domains:
            for d in domains:
                domain.append(d)

        search_timetables = self.env['siantou.ems.timetable.timetable'].search(domain)

        key_timetables = {}
        info_timetables = {}
        for search_timetable in search_timetables:
            if not search_timetable.date or not search_timetable.day_of_week or not search_timetable.employee_id.id:
                continue
            key = '{}-{}'.format(search_timetable.semester_id.id, search_timetable.class_id.id)
            semester = '{}'.format(search_timetable.semester_id.name)
            study = '{} - {} - {} - {}'.format(search_timetable.class_id.name, search_timetable.field_of_study_id.name, search_timetable.specialty_id.name if search_timetable.specialty_id.id else '', search_timetable.level_id.name, search_timetable.batch_id.name)
            if key not in key_timetables:
                key_timetables[key] = []
                info_timetables[key] = {}
                info_timetables[key]['semester'] = semester
                info_timetables[key]['study'] = study
                info_timetables[key]['filter'] = self.env['ir.config_parameter'].sudo().get_param(f'siantou.filter_user_{self.env.user.id}', '')
            timetable = {}
            timetable['id'] = search_timetable.id
            timetable['date'] = search_timetable.date
            timetable['date_of_week'] = datetime.strftime(search_timetable.date, DATE_FORMAT_FR)
            timetable['semester_name'] = search_timetable.semester_id.name
            timetable['cycle_id'] = search_timetable.cycle_id.id
            timetable['cycle_name'] = search_timetable.cycle_id.name
            timetable['level_id'] = search_timetable.level_id.id
            timetable['level_name'] = search_timetable.level_id.name
            timetable['field_of_study_id'] = search_timetable.field_of_study_id.id
            timetable['field_of_study_name'] = search_timetable.field_of_study_id.name
            timetable['specialty_id'] = search_timetable.specialty_id.id
            timetable['specialty_name'] = search_timetable.specialty_id.name
            timetable['option_id'] = search_timetable.option_id.id
            timetable['option_name'] = search_timetable.option_id.name
            timetable['class_id'] = search_timetable.class_id.id
            timetable['class_name'] = search_timetable.class_id.name
            timetable['department_id'] = search_timetable.department_id.id
            timetable['department_name'] = search_timetable.department_id.name
            timetable['school_id'] = search_timetable.school_id.id
            timetable['school_name'] = search_timetable.school_id.name
            timetable['subject_id'] = search_timetable.subject_id.id
            timetable['subject_name'] = search_timetable.subject_id.name
            timetable['subject_code'] = search_timetable.subject_id.code
            timetable['subject_hours_credit'] = search_timetable.subject_id.hours_credit
            timetable['subject_shared_subject'] = '(TC)' if search_timetable.subject_id.shared_subject else ''
            timetable['classroom_name'] = search_timetable.classroom_id.name
            timetable['building_name'] = search_timetable.classroom_id.building_id.name
            timetable['batch_name'] = search_timetable.batch_id.name
            timetable['employee_name'] = search_timetable.employee_id.name
            timetable['day_of_week'] = CURRENT_WEEKDAY[search_timetable.day_of_week]
            timetable['start_time'] = search_timetable.start_time
            timetable['end_time'] = search_timetable.end_time
            timetable['worked_start_time'] = search_timetable.worked_start_time
            timetable['worked_end_time'] = search_timetable.worked_end_time
            timetable['reason'] = search_timetable.reason
            timetable['not_active_slotitems'] = search_timetable.not_active_slotitems
            timetable['status'] = STATUS_TIMETABLE[search_timetable.status]
            key_timetables[key].append(timetable)

        for key in key_timetables.keys():
            if len(key_timetables[key]) > 0:
                specialty_id = key_timetables[key][0]['specialty_id']

                slots = self.env['siantou.ems.timetable.slot'].search([
                    ('is_active', '=', False),
                ])
                slots = list(slots)

                available_slotitem = None
                for slot in slots:
                    specialty_ids = list(slot.specialty_ids)
                    for specialty in specialty_ids:
                        if specialty.id == specialty_id:
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

                key_timetables[key] = TimetablePrintWizard.format_timetable(key_timetables[key], not_active_slotitems)
            else:
                key_timetables[key] = TimetablePrintWizard.format_timetable(key_timetables[key])
            for monday in key_timetables[key].keys():
                for i, timetable in enumerate(key_timetables[key][monday]['Heure']):
                    tm = timetable.split('-')
                    tm[0] = TimetablePrintWizard.convert_float_to_time(tm[0])
                    tm[1] = TimetablePrintWizard.convert_float_to_time(tm[1])
                    key_timetables[key][monday]['Heure'][i] = '{}-{}'.format(tm[0], tm[1])
                hours = [(i[0] + 1) for i in sorted(enumerate(key_timetables[key][monday]['Heure']), key=lambda x: x[1])]
                key_timetables[key][monday]['Heure'] = TimetablePrintWizard.sort_by_indexes(key_timetables[key][monday]['Heure'], hours)
                key_timetables[key][monday]['Lundi'] = TimetablePrintWizard.sort_by_indexes(key_timetables[key][monday]['Lundi'], hours)
                key_timetables[key][monday]['Mardi'] = TimetablePrintWizard.sort_by_indexes(key_timetables[key][monday]['Mardi'], hours)
                key_timetables[key][monday]['Mercredi'] = TimetablePrintWizard.sort_by_indexes(key_timetables[key][monday]['Mercredi'], hours)
                key_timetables[key][monday]['Jeudi'] = TimetablePrintWizard.sort_by_indexes(key_timetables[key][monday]['Jeudi'], hours)
                key_timetables[key][monday]['Vendredi'] = TimetablePrintWizard.sort_by_indexes(key_timetables[key][monday]['Vendredi'], hours)
                key_timetables[key][monday]['Samedi'] = TimetablePrintWizard.sort_by_indexes(key_timetables[key][monday]['Samedi'], hours)
                key_timetables[key][monday]['Dimanche'] = TimetablePrintWizard.sort_by_indexes(key_timetables[key][monday]['Dimanche'], hours)
            key_timetables[key] = TimetablePrintWizard.paginate_calendar(key_timetables[key], len(key_timetables[key].keys()))
            key_timetables[key]['semester'] = info_timetables[key]['semester']
            key_timetables[key]['study'] = info_timetables[key]['study']
            key_timetables[key]['filter'] = info_timetables[key]['filter']

        _logger.info(f'----------- tototototototo key_timetables {key_timetables} -----------')

        return {
            'docdata': {
                'timetable_data': key_timetables,
            }
        }

    def sort_timetable_percentage(self, timetable_percentage):
        name = timetable_percentage[1]['name'] if timetable_percentage[1]['name'] else ''
        name = name.strip()
        name = name.lower()
        return name

    def print_timetable_percentage_report_data(self, domains=None, all_domains=None, status=None):
        # Récupérer les emplois du temps pour le semestre sélectionné
        domain = []

        if domains:
            for d in domains:
                domain.append(d)

        search_timetable_percentages = self.env['siantou.ems.timetable.timetable'].search(domain)

        all_domain = []

        if all_domains:
            for d in all_domains:
                all_domain.append(d)

        search_all_timetable_percentages = self.env['siantou.ems.timetable.timetable'].search(all_domain)

        total_all_timetable_percentage_count = 0
        total_timetable_percentage_count = {}
        for search_all_timetable_percentage in search_all_timetable_percentages:
            if not search_all_timetable_percentage.date or not search_all_timetable_percentage.day_of_week or not search_all_timetable_percentage.employee_id.id:
                continue
            key = '{}'.format(search_all_timetable_percentage.employee_id.id)
            if key not in total_timetable_percentage_count:
                total_timetable_percentage_count[key] = 1
            else:
                total_timetable_percentage_count[key] += 1
            total_all_timetable_percentage_count += 1

        key_timetable_percentages = {}
        info_timetable_percentages = {}
        for search_timetable_percentage in search_timetable_percentages:
            if not search_timetable_percentage.date or not search_timetable_percentage.day_of_week or not search_timetable_percentage.employee_id.id:
                continue
            key = '{}'.format(search_timetable_percentage.employee_id.id)
            if key not in key_timetable_percentages:
                key_timetable_percentages[key] = {}
                key_timetable_percentages[key]['name'] = search_timetable_percentage.employee_id.name
                key_timetable_percentages[key]['identifier'] = search_timetable_percentage.employee_id.identifier
                key_timetable_percentages[key]['data'] = []
                key_timetable_percentages[key]['percentage'] = 0.0
                key_timetable_percentages[key]['class'] = ''
            timetable_percentage = {}
            timetable_percentage['id'] = search_timetable_percentage.id
            timetable_percentage['date'] = search_timetable_percentage.date
            timetable_percentage['date_of_week'] = datetime.strftime(search_timetable_percentage.date, DATE_FORMAT_FR)
            timetable_percentage['semester_name'] = search_timetable_percentage.semester_id.name
            timetable_percentage['cycle_id'] = search_timetable_percentage.cycle_id.id
            timetable_percentage['cycle_name'] = search_timetable_percentage.cycle_id.name
            timetable_percentage['level_id'] = search_timetable_percentage.level_id.id
            timetable_percentage['level_name'] = search_timetable_percentage.level_id.name
            timetable_percentage['field_of_study_id'] = search_timetable_percentage.field_of_study_id.id
            timetable_percentage['field_of_study_name'] = search_timetable_percentage.field_of_study_id.name
            timetable_percentage['specialty_id'] = search_timetable_percentage.specialty_id.id
            timetable_percentage['specialty_name'] = search_timetable_percentage.specialty_id.name
            timetable_percentage['option_id'] = search_timetable_percentage.option_id.id
            timetable_percentage['option_name'] = search_timetable_percentage.option_id.name
            timetable_percentage['class_id'] = search_timetable_percentage.class_id.id
            timetable_percentage['class_name'] = search_timetable_percentage.class_id.name
            timetable_percentage['department_id'] = search_timetable_percentage.department_id.id
            timetable_percentage['department_name'] = search_timetable_percentage.department_id.name
            timetable_percentage['school_id'] = search_timetable_percentage.school_id.id
            timetable_percentage['school_name'] = search_timetable_percentage.school_id.name
            timetable_percentage['subject_id'] = search_timetable_percentage.subject_id.id
            timetable_percentage['subject_name'] = search_timetable_percentage.subject_id.name
            timetable_percentage['subject_code'] = search_timetable_percentage.subject_id.code
            timetable_percentage['subject_hours_credit'] = search_timetable_percentage.subject_id.hours_credit
            timetable_percentage['subject_shared_subject'] = '(TC)' if search_timetable_percentage.subject_id.shared_subject else ''
            timetable_percentage['classroom_name'] = search_timetable_percentage.classroom_id.name
            timetable_percentage['building_name'] = search_timetable_percentage.classroom_id.building_id.name
            timetable_percentage['batch_name'] = search_timetable_percentage.batch_id.name
            timetable_percentage['employee_id'] = search_timetable_percentage.employee_id.id
            timetable_percentage['identifier'] = search_timetable_percentage.employee_id.identifier
            timetable_percentage['employee_name'] = search_timetable_percentage.employee_id.name
            timetable_percentage['day_of_week'] = CURRENT_WEEKDAY[search_timetable_percentage.day_of_week]
            timetable_percentage['start_time'] = TimetablePrintWizard.convert_float_to_time(search_timetable_percentage.start_time)
            timetable_percentage['end_time'] = TimetablePrintWizard.convert_float_to_time(search_timetable_percentage.end_time)
            timetable_percentage['worked_start_time'] = TimetablePrintWizard.convert_float_to_time(search_timetable_percentage.worked_start_time)
            timetable_percentage['worked_end_time'] = TimetablePrintWizard.convert_float_to_time(search_timetable_percentage.worked_end_time)
            timetable_percentage['reason'] = search_timetable_percentage.reason
            timetable_percentage['not_active_slotitems'] = search_timetable_percentage.not_active_slotitems
            timetable_percentage['status'] = STATUS_TIMETABLE[search_timetable_percentage.status]
            key_timetable_percentages[key]['data'].append(timetable_percentage)

        all_timetable_percentage_count = 0
        for key in key_timetable_percentages.keys():
            if key in total_timetable_percentage_count:
                timetable_percentage_count = len(key_timetable_percentages[key]['data'])
                if total_timetable_percentage_count[key] > 0:
                    key_timetable_percentages[key]['percentage'] = (timetable_percentage_count / total_timetable_percentage_count[key]) * 100
                    key_timetable_percentages[key]['percentage'] = round(key_timetable_percentages[key]['percentage'], 2)
                    if status in ['present', 'punctuality']:
                        if key_timetable_percentages[key]['percentage'] >= 90.0:
                            key_timetable_percentages[key]['class'] = 'text-success'
                        if key_timetable_percentages[key]['percentage'] >= 80.0 and key_timetable_percentages[key]['percentage'] < 90.0:
                            key_timetable_percentages[key]['class'] = 'text-warning'
                        if key_timetable_percentages[key]['percentage'] < 80.0:
                            key_timetable_percentages[key]['class'] = 'text-danger'
                    else:
                        if key_timetable_percentages[key]['percentage'] < 10.0:
                            key_timetable_percentages[key]['class'] = 'text-success'
                        if key_timetable_percentages[key]['percentage'] >= 10.0 and key_timetable_percentages[key]['percentage'] < 20.0:
                            key_timetable_percentages[key]['class'] = 'text-warning'
                        if key_timetable_percentages[key]['percentage'] >= 20.0:
                            key_timetable_percentages[key]['class'] = 'text-danger'
                all_timetable_percentage_count += timetable_percentage_count

        total_percentage = 0.0
        if total_all_timetable_percentage_count > 0:
            total_percentage = (all_timetable_percentage_count / total_all_timetable_percentage_count) * 100
            total_percentage = round(total_percentage, 2)

        key_timetable_percentages = sorted(key_timetable_percentages.items(), key=self.sort_timetable_percentage)
        key_timetable_percentages = dict(key_timetable_percentages)

        _logger.info(f'----------- tototototototo key_timetable_percentages {key_timetable_percentages} -----------')

        title = self.env['ir.config_parameter'].sudo().get_param(f'siantou.filter_user_{self.env.user.id}', '')

        return {
            'docdata': {
                'filter': title,
                'timetable_percentage_data': key_timetable_percentages,
                'total_percentage': total_percentage,
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
    def sort_by_indexes(lst, indexes, reverse=False):
        return [val for (_, val) in sorted(zip(indexes, lst), key=lambda x: x[0], reverse=reverse)]

    @staticmethod
    def format_timetable(data, hours=[]):
        n = 0.0
        current_data = []
        current_hours = []
        key_timetables = {}
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
                if TimetablePrintWizard.increment_float_time(hours[i][0], n) == 0.0:
                    h = '{}-{}'.format(TimetablePrintWizard.increment_float_time(hours[i][0]), TimetablePrintWizard.increment_float_time(hours[i][1]))
                    current_hours.append(h)
                    hours[i][0] = TimetablePrintWizard.increment_float_time(hours[i][1])
                else:
                    if TimetablePrintWizard.increment_float_time(hours[i][0], n) < TimetablePrintWizard.increment_float_time(hours[i][1]):
                        h = '{}-{}'.format(TimetablePrintWizard.increment_float_time(hours[i][0]), TimetablePrintWizard.increment_float_time(hours[i][0], n))
                        current_hours.append(h)
                        hours[i][0] = TimetablePrintWizard.increment_float_time(hours[i][0], n)
                    else:
                        h = '{}-{}'.format(TimetablePrintWizard.increment_float_time(hours[i][0]), TimetablePrintWizard.increment_float_time(hours[i][1]))
                        current_hours.append(h)
                        hours[i][0] = TimetablePrintWizard.increment_float_time(hours[i][1])

        current_hours = list(set(current_hours))
        current_hours.sort(key=lambda h: float(h.split('-')[0]))

        for d in sorted_data:
            if d['date'].weekday() == 0:
                monday = d['date']
            else:
                monday = d['date'] - timedelta(days=d['date'].weekday())
            monday = datetime.strftime(monday, DATE_FORMAT)
            if monday not in key_timetables:
                key_timetables[monday] = {
                    'Heure': [hour for hour in current_hours],
                    'Lundi': [],
                    'Mardi': [],
                    'Mercredi': [],
                    'Jeudi': [],
                    'Vendredi': [],
                    'Samedi': [],
                    'Dimanche': [],
                }

                for i in range(len(key_timetables[monday]['Heure'])):
                    for key in key_timetables[monday].keys():
                        if key == 'Heure':
                            continue
                        key_timetables[monday][key].append(np.nan)
            if monday not in df:
                df[monday] = pd.DataFrame(key_timetables[monday], dtype=str)
            while TimetablePrintWizard.increment_float_time(d['start_time']) < TimetablePrintWizard.increment_float_time(d['end_time']):
                if TimetablePrintWizard.increment_float_time(d['start_time'], n) == 0.0:
                    h = '{}-{}'.format(TimetablePrintWizard.increment_float_time(d['start_time']), TimetablePrintWizard.increment_float_time(d['end_time']))
                    for i, row in df[monday].iterrows():
                        if h == key_timetables[monday]['Heure'][i]:
                            for j, column in enumerate(df[monday].columns):
                                for k, key in enumerate(key_timetables[monday].keys()):
                                    if k == d['date'].weekday() + 1:
                                        if column == key:
                                            if TimetablePrintWizard.is_float(str(df[monday].loc[i, column])) and np.isnan(float(str(df[monday].loc[i, column]))):
                                                df[monday].loc[i, column] = str(d['id'])
                                            else:
                                                df[monday].loc[i, column] = '{}-{}'.format(df[monday].loc[i, column], str(d['id']))
                                        break
                    d['start_time'] = TimetablePrintWizard.increment_float_time(d['end_time'])
                else:
                    if TimetablePrintWizard.increment_float_time(d['start_time'], n) < TimetablePrintWizard.increment_float_time(d['end_time']):
                        h = '{}-{}'.format(TimetablePrintWizard.increment_float_time(d['start_time']), TimetablePrintWizard.increment_float_time(d['start_time'], n))
                        for i, row in df[monday].iterrows():
                            if h == key_timetables[monday]['Heure'][i]:
                                for j, column in enumerate(df[monday].columns):
                                    for k, key in enumerate(key_timetables[monday].keys()):
                                        if k == d['date'].weekday() + 1:
                                            if column == key:
                                                if TimetablePrintWizard.is_float(str(df[monday].loc[i, column])) and np.isnan(float(str(df[monday].loc[i, column]))):
                                                    df[monday].loc[i, column] = str(d['id'])
                                                else:
                                                    df[monday].loc[i, column] = '{}-{}'.format(df[monday].loc[i, column], str(d['id']))
                                            break
                        d['start_time'] = TimetablePrintWizard.increment_float_time(d['start_time'], n)
                    else:
                        h = '{}-{}'.format(TimetablePrintWizard.increment_float_time(d['start_time']), TimetablePrintWizard.increment_float_time(d['end_time']))
                        for i, row in df[monday].iterrows():
                            if h == key_timetables[monday]['Heure'][i]:
                                for j, column in enumerate(df[monday].columns):
                                    for k, key in enumerate(key_timetables[monday].keys()):
                                        if k == d['date'].weekday() + 1:
                                            if column == key:
                                                if TimetablePrintWizard.is_float(str(df[monday].loc[i, column])) and np.isnan(float(str(df[monday].loc[i, column]))):
                                                    df[monday].loc[i, column] = str(d['id'])
                                                else:
                                                    df[monday].loc[i, column] = '{}-{}'.format(df[monday].loc[i, column], str(d['id']))
                                            break
                        d['start_time'] = TimetablePrintWizard.increment_float_time(d['end_time'])

        for monday in df.keys():
            df[monday].replace(np.nan, '-', inplace=True)

            for key in key_timetables[monday].keys():
                key_timetables[monday][key] = list(df[monday][key])
                if key != 'Heure':
                    for i, vals in enumerate(key_timetables[monday][key]):
                        key_timetables[monday][key][i] = []
                        if vals != '-':
                            for v in vals.split('-'):
                                key_timetables[monday][key][i].append([d for d in data if d['id'] == int(v)][0])

            monday = datetime.strptime(f"{monday}", DATE_FORMAT).date()
            saturday = monday + timedelta(days=5)
            monday_fr = datetime.strftime(monday, DATE_FORMAT_FR)
            saturday_fr = datetime.strftime(saturday, DATE_FORMAT_FR)
            monday = datetime.strftime(monday, DATE_FORMAT)
            saturday = '{} - {}'.format(monday_fr, saturday_fr)
            key_timetables[saturday] = key_timetables[monday]
            del(key_timetables[monday])

        _logger.info(f'----------- tototototototo key_timetables {key_timetables} -----------')

        return key_timetables

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
