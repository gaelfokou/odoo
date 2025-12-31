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

TYPE_COUR = {
    'cj': 'Cours du jour',
    'cs': 'Cours du soir',
}

STATUS_ATTENDANCE = {
    'paid': 'Payé',
    'unpaid': 'Non payé',
}

_logger = logging.getLogger(__name__)

class TeacherTimetableAttendanceFilterWizard(models.TransientModel):
    _name = 'teacher.timetable.attendance.filter.wizard'
    _description = 'Filtre des émargements des enseignants'

    # Enseignant lié à la programmation de cours
    employee_id = fields.Many2one(
        'hr.employee',
        'Enseignant',
    )

    is_teacher = fields.Boolean(
        'Est un enseignant',
        default=True,
    )

    is_permanent = fields.Boolean(
        'Est un permanent',
        default=False,
    )

    def _default_start_date(self):
        start_date = date.today().replace(day=1)
        return start_date

    start_date = fields.Date(
        'Date de début',
        default=_default_start_date,
    )

    def _default_end_date(self):
        end_date = (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()
        return end_date

    end_date = fields.Date(
        'Date de fin',
        default=_default_end_date,
    )

    status = fields.Selection([
        ('paid', 'Payé'),
        ('unpaid', 'Non payé'),
    ], 'Statut',
        # default='unpaid',
    )

    has_rate = fields.Boolean(
        'Taux horaire défini',
        default=False,
    )

    # Contrainte logique pour s'assurer que les dates de début et de fin sont définies et que la date de fin est supérieure à la date de début
    @api.constrains('start_date', 'end_date')
    def _constrains_date(self):
        for record in self:
            if record.start_date > record.end_date:
                raise ValidationError("La date de fin doit être supérieure à la date de début")

    def action_filter(self):
        self.env['teacher.timetable.attendance']._transient_vacuum()
        self.env['teacher.timetable.attendance'].search([('create_uid', '=', self.env.user.id)]).unlink()

        domain = []
        title = []

        domain.append('|')
        domain.append('&')
        domain.append(('group_id.is_active', '=', True))
        domain.append(('group_id.is_submit', '=', False))
        domain.append('&')
        domain.append(('group_parent_id.is_active', '=', True))
        domain.append(('group_parent_id.is_submit', '=', False))
        domain.append(('status', 'in', ['present', 'permission']))

        if self.is_permanent:
            title.append('Est un permanent')

        domain.append(('employee_id.is_teacher', '=', True))
        domain.append(('employee_id.is_permanent', '=', self.is_permanent))

        if self.employee_id.id:
            domain.append(('employee_id', '=', self.employee_id.id))
            title.append(self.employee_id.name)

        order = 'date asc, id asc'

        search_consumptionhours = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
        key_consumptionhours = {}
        consumptionhours = []
        for search_consumptionhour in search_consumptionhours:
            if not search_consumptionhour.date or not search_consumptionhour.day_of_week:
                continue

            end_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(search_consumptionhour.end_time, True)
            start_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(search_consumptionhour.start_time, True)
            key = '{}-{}-{}-{}'.format(search_consumptionhour.class_id.id, search_consumptionhour.date, start_time, end_time)
            if key not in key_consumptionhours:
                key_consumptionhours[key] = search_consumptionhour
            else:
                continue

            consumptionhour = {}
            consumptionhour['id'] = search_consumptionhour.id
            consumptionhour['name'] = search_consumptionhour.name
            consumptionhour['date'] = search_consumptionhour.date
            consumptionhour['date_of_week'] = datetime.strftime(search_consumptionhour.date, DATE_FORMAT_FR)
            consumptionhour['semester_name'] = search_consumptionhour.semester_id.name
            consumptionhour['cycle_name'] = search_consumptionhour.cycle_id.name
            consumptionhour['level_name'] = search_consumptionhour.level_id.name
            consumptionhour['field_of_study_id'] = search_consumptionhour.field_of_study_id.id
            consumptionhour['field_of_study_name'] = search_consumptionhour.field_of_study_id.name
            consumptionhour['specialty_name'] = search_consumptionhour.specialty_id.name
            consumptionhour['option_name'] = search_consumptionhour.option_id.name
            consumptionhour['class_id'] = search_consumptionhour.class_id.id
            consumptionhour['class_name'] = search_consumptionhour.class_id.name
            consumptionhour['department_id'] = search_consumptionhour.department_id.id
            consumptionhour['department_name'] = search_consumptionhour.department_id.name
            consumptionhour['subject_id'] = search_consumptionhour.subject_id.id
            consumptionhour['subject_name'] = search_consumptionhour.subject_id.name
            consumptionhour['subject_code'] = search_consumptionhour.subject_id.code
            consumptionhour['subject_hours_credit'] = search_consumptionhour.subject_id.hours_credit
            consumptionhour['subject_shared_subject'] = search_consumptionhour.subject_id.shared_subject
            consumptionhour['classroom_name'] = search_consumptionhour.classroom_id.name
            consumptionhour['building_name'] = search_consumptionhour.classroom_id.building_id.name
            consumptionhour['batch_name'] = search_consumptionhour.batch_id.name
            consumptionhour['employee_name'] = search_consumptionhour.employee_id.name
            consumptionhour['day_of_week'] = CURRENT_WEEKDAY[search_consumptionhour.day_of_week]
            consumptionhour['start_time'] = search_consumptionhour.start_time
            consumptionhour['end_time'] = search_consumptionhour.end_time
            consumptionhour['worked_start_time'] = search_consumptionhour.worked_start_time
            consumptionhour['worked_end_time'] = search_consumptionhour.worked_end_time
            consumptionhour['not_active_slotitems'] = search_consumptionhour.not_active_slotitems
            consumptionhour['status'] = search_consumptionhour.status
            consumptionhours.append(consumptionhour)
        consumptionhours = TeacherTimetableAttendanceFilterWizard.format_consumptionhour(consumptionhours)

        timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
        if self.start_date and self.end_date:
            start_date = datetime.strftime(self.start_date, DATE_FORMAT_FR)
            end_date = datetime.strftime(self.end_date, DATE_FORMAT_FR)
            title.append('{} - {}'.format(start_date, end_date))
            timetables = timetables.filtered(lambda rec: rec.date and rec.day_of_week and rec.date >= self.start_date and rec.date <= self.end_date)

        order = 'date_from asc'
        key_payslips = {}
        employee_ids = []
        for timetable in timetables:
            if timetable.employee_id.id not in employee_ids:
                paymenthistories = self.env['hr.payslip'].search([('employee_id', '=', timetable.employee_id.id)], order=order)
                paymenthistories = list(paymenthistories)
                for paymenthistory in paymenthistories:
                    for worked_days_line_id in paymenthistory.worked_days_line_ids:
                        end_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(worked_days_line_id.timetable_id.end_time, True)
                        start_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(worked_days_line_id.timetable_id.start_time, True)
                        key = '{}-{}-{}-{}'.format(worked_days_line_id.timetable_id.employee_id.id, worked_days_line_id.timetable_id.date, start_time, end_time)
                        if key not in key_payslips:
                            key_payslips[key] = {}
                            key_payslips[key]['timetable_id'] = worked_days_line_id.timetable_id.id
                            key_payslips[key]['rate'] = worked_days_line_id.rate
                            key_payslips[key]['amount'] = worked_days_line_id.amount
                employee_ids.append(timetable.employee_id.id)

        timetable_ids = [payslip['timetable_id'] for payslip in key_payslips.values()]

        if self.status:
            title.append(STATUS_ATTENDANCE[self.status])
            if self.status == 'paid':
                timetables = timetables.filtered(lambda rec: rec.id in timetable_ids)
            elif self.status == 'unpaid':
                timetables = timetables.filtered(lambda rec: rec.id not in timetable_ids)

        key_timetables = {}
        for timetable in timetables:
            if not timetable.date or not timetable.day_of_week:
                continue

            end_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(timetable.end_time, True)
            start_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(timetable.start_time, True)
            key = '{}-{}-{}-{}'.format(timetable.employee_id.id, timetable.date, start_time, end_time)
            if key in key_payslips and key_payslips[key]['timetable_id'] != timetable.id:
                continue
            if key not in key_timetables:
                key_timetables[key] = timetable
            else:
                continue

            if timetable.status == 'present':
                end_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(timetable.worked_end_time, True)
                start_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(timetable.worked_start_time, True)
                end_time = datetime.strptime(f"{timetable.date} {end_time}", DATETIME_FORMAT)
                start_time = datetime.strptime(f"{timetable.date} {start_time}", DATETIME_FORMAT)

                worked_hours = end_time - start_time
                worked_hours = worked_hours.total_seconds() / 3600.0
                worked_hours = round(worked_hours, 2)
            elif timetable.status == 'permission':
                end_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(timetable.end_time, True)
                start_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(timetable.start_time, True)
                end_time = datetime.strptime(f"{timetable.date} {end_time}", DATETIME_FORMAT)
                start_time = datetime.strptime(f"{timetable.date} {start_time}", DATETIME_FORMAT)

                worked_hours = end_time - start_time
                worked_hours = worked_hours.total_seconds() / 3600.0
                worked_hours = round(worked_hours, 2)
            else:
                end_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(0.0, True)
                start_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(0.0, True)
                end_time = datetime.strptime(f"{timetable.date} {end_time}", DATETIME_FORMAT)
                start_time = datetime.strptime(f"{timetable.date} {start_time}", DATETIME_FORMAT)

                worked_hours = end_time - start_time
                worked_hours = worked_hours.total_seconds() / 3600.0
                worked_hours = round(worked_hours, 2)

            if worked_hours < 0.0:
                continue

            if len(timetable.employee_id.diplome_ids.ids) > 0:
                domain = [
                    ('school_id', '=', timetable.school_id.id),
                    ('cycle_id', '=', timetable.cycle_id.id),
                    ('level_id', '=', timetable.level_id.id),
                    ('type_cour', '=', timetable.type_cour),
                    ('diplome_availability_id.diplome_ids', 'in', timetable.employee_id.diplome_ids.ids),
                ]
            else:
                domain = [
                    ('school_id', '=', timetable.school_id.id),
                    ('cycle_id', '=', timetable.cycle_id.id),
                    ('level_id', '=', timetable.level_id.id),
                    ('type_cour', '=', timetable.type_cour),
                ]

            hourly_rates = self.env['siantou.ems.core.hourly.rate'].search(domain)
            hourly_rates = list(hourly_rates)

            min_hourly_rate = None
            min_teacher_hourly_rate = None
            if len(hourly_rates) > 0:
                for hourly_rate in hourly_rates:
                    domain = [
                        ('hourly_rate_id', '=', hourly_rate.id),
                        ('employee_id', '=', timetable.employee_id.id),
                        # ('subject_id', '=', timetable.subject_id.id),
                    ]

                    teacher_hourly_rates = self.env['siantou.ems.core.teacher.hourly.rate'].search(domain, limit=1)
                    teacher_hourly_rates = list(teacher_hourly_rates)
                    if len(teacher_hourly_rates) > 0:
                        for teacher_hourly_rate in teacher_hourly_rates:
                            if not min_teacher_hourly_rate:
                                min_teacher_hourly_rate = teacher_hourly_rate.rate
                            else:
                                if teacher_hourly_rate.rate < min_teacher_hourly_rate:
                                    min_teacher_hourly_rate = teacher_hourly_rate.rate
                    if not min_hourly_rate:
                        min_hourly_rate = hourly_rate.rate
                    else:
                        if hourly_rate.rate < min_hourly_rate:
                            min_hourly_rate = hourly_rate.rate

            if min_teacher_hourly_rate:
                rate = min_teacher_hourly_rate
            elif min_hourly_rate:
                rate = min_hourly_rate
            else:
                rate = 0.0

            amount = rate * worked_hours
            amount = round(amount, 2)

            if timetable.employee_id.is_permanent:
                rate = 0.0
                amount = 0.0

            if key in key_payslips:
                rate = key_payslips[key]['rate']
                amount = key_payslips[key]['amount']

            if self.has_rate:
                if rate == 0.0:
                    continue

            hours_credit = 0.0
            total_all = 0.0
            total_done = 0.0
            total_awaiting = 0.0
            key_class = '{}'.format(timetable.class_id.id)
            key_subject = '{}'.format(timetable.subject_id.id)
            if key_class in consumptionhours:
                if key_subject in consumptionhours[key_class]['data']:
                    hours_credit = consumptionhours[key_class]['data'][key_subject]['data']['credit']
                    total_all = consumptionhours[key_class]['data'][key_subject]['data']['done']
                    total_done = consumptionhours[key_class]['data'][key_subject]['data']['done']
                    total_awaiting = consumptionhours[key_class]['data'][key_subject]['data']['awaiting']

            teacher_timetable_attendance = self.env['teacher.timetable.attendance'].create({
                'timetable_id': timetable.id,
                'worked_time': worked_hours,
                'rate': rate,
                'amount': amount,
                'hours_credit': hours_credit,
                'total_all': total_all,
                'total_done': total_done,
                'total_awaiting': total_awaiting,
                'status': timetable.status,
                'start_date': self.start_date,
                'end_date': self.end_date,
                'is_paid': True if timetable.id in timetable_ids else False,
            })

        if len(title) > 0:
            title = ' / '.join(title)
        else:
            title = 'Non spécifié'

        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', title)

        view_id = self.env.ref('siantou_ems_core.timetable_tree_view').id
        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'teacher.timetable.attendance',
            'views': [(view_id, 'tree'), (False, 'form')],
            'view_id': view_id,
            'target': 'main',
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
                consumptionhours[key_class]['data'][key_subject]['data']['done'] = sum([TeacherTimetableAttendanceFilterWizard.convert_number_of_hours(v) for v in consumptionhours[key_class]['data'][key_subject]['data']['done']])
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
    def convert_number_of_hours(tm):
        end_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(tm['end_time'], True)
        start_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(tm['start_time'], True)
        datetime_to = datetime.strptime(f"{tm['date']} {end_time}", DATETIME_FORMAT)
        datetime_from = datetime.strptime(f"{tm['date']} {start_time}", DATETIME_FORMAT)
        weekly_hours_credit = datetime_to - datetime_from
        weekly_hours_credit = weekly_hours_credit - timedelta(hours=tm['not_active_slotitems'])
        weekly_hours_credit = weekly_hours_credit.total_seconds() / 3600.0
        weekly_hours_credit = round(weekly_hours_credit, 2)
        return weekly_hours_credit
