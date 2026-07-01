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
        'Est un enseignant ?',
        default=True,
    )

    is_permanent = fields.Boolean(
        'Est un permanent ?',
        default=False,
    )

    is_temporary = fields.Boolean(
        'Est un vacataire ?',
        compute='_compute_temporary',
    )

    @api.depends('is_permanent')
    def _compute_temporary(self):
        for record in self:
            record.is_temporary = not record.is_permanent

    @api.onchange('is_permanent')
    def _onchange_temporary(self):
        for record in self:
            record.is_temporary = not record.is_permanent

    def _default_start_date(self):
        start_date = date.today().replace(day=1)
        return start_date

    start_date = fields.Date(
        string='Date de début',
        default=_default_start_date,
    )

    def _default_end_date(self):
        end_date = (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()
        return end_date

    end_date = fields.Date(
        string='Date de fin',
        default=_default_end_date,
    )

    status = fields.Selection([
        ('paid', 'Payé'),
        ('unpaid', 'Non payé'),
    ], string='Statut',
        # default='unpaid',
    )

    has_rate = fields.Boolean(
        'Taux horaire défini ?',
        default=False,
    )

    refundable_additional = fields.Boolean(
        'Supplément remboursable ?',
        default=False,
    )

    sort_type = fields.Selection([
        ('teacher', 'Par enseignant'),
        ('hour', 'Par heure'),
    ], string='Ordre d\'impression',
        # default='teacher',
    )

    employee_id_domain = fields.Binary(compute='_compute_employee_domain', default=[])

    @api.depends('is_teacher', 'is_permanent')
    def _compute_employee_domain(self):
        for record in self:
            domain = []
            if record.is_teacher:
                domain.append(('is_teacher', '=', True))
            if record.is_permanent:
                domain.append(('is_permanent', '=', True))
            else:
                domain.append(('is_permanent', '=', False))
            record.employee_id_domain = domain

    @api.constrains('start_date', 'end_date')
    def _constrains_date(self):
        for record in self:
            if record.start_date > record.end_date:
                raise ValidationError("La date de fin doit être supérieure ou égale à la date de début")

    def action_filter(self):
        self.env['teacher.timetable.attendance']._transient_vacuum()
        self.env['teacher.timetable.attendance'].search([('create_uid', '=', self.env.user.id)]).unlink()

        search_consumptionhours = self.consumptionhour(end_date=self.end_date)
        consumptionhours = []
        for search_consumptionhour in search_consumptionhours:
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
            consumptionhour['class_group_id'] = search_consumptionhour.class_group_id.id if search_consumptionhour.class_group_id.id else None
            consumptionhour['class_group_name'] = search_consumptionhour.class_group_id.name if search_consumptionhour.class_group_id.id else ''
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
            consumptionhour['status'] = search_consumptionhour.status
            consumptionhours.append(consumptionhour)
        consumptionhours = TeacherTimetableAttendanceFilterWizard.format_consumptionhour(consumptionhours)

        domain = []
        title = []
        domain.append('|')
        domain.append('&')
        domain.append('&')
        domain.append(('group_id.is_active', '=', True))
        domain.append(('group_id.is_submit', '=', False))
        domain.append(('group_id.status', '=', 'valid'))
        domain.append('&')
        domain.append('&')
        domain.append('&')
        domain.append(('group_parent_id.is_active', '=', True))
        domain.append(('group_parent_id.is_submit', '=', False))
        domain.append(('group_parent_id.status', '=', 'valid'))
        domain.append(('group_id.status', '=', 'valid'))
        domain.append(('is_active', '=', True))
        domain.append(('status', 'in', ['present', 'permission']))

        if self.is_teacher:
            domain.append(('employee_id.is_teacher', '=', True))
            title.append('Est un enseignant')
        if self.is_permanent:
            domain.append(('employee_id.is_permanent', '=', True))
            title.append('Est un permanent')
        else:
            domain.append(('employee_id.is_permanent', '=', False))
            title.append('Est un vacataire')

        if self.employee_id.id:
            domain.append(('employee_id', '=', self.employee_id.id))
            title.append(self.employee_id.name)

        order = 'date asc, id asc'

        timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
        if self.start_date and self.end_date:
            start_date = datetime.strftime(self.start_date, DATE_FORMAT_FR)
            end_date = datetime.strftime(self.end_date, DATE_FORMAT_FR)
            title.append('{} - {}'.format(start_date, end_date))
            timetables = timetables.filtered(lambda rec: rec.date and rec.day_of_week and rec.date >= self.start_date and rec.date <= self.end_date)

        if self.refundable_additional:
            title.append('Supplément remboursable')

        order = 'date_from asc'
        key_payslips = {}
        key_extended_hours = {}
        employee_ids = []
        for timetable in timetables:
            if timetable.employee_id.id not in employee_ids:
                paymenthistories = self.env['hr.payslip'].search([('employee_id', '=', timetable.employee_id.id)], order=order)
                paymenthistories = list(paymenthistories)
                for paymenthistory in paymenthistories:
                    for worked_days_line_id in paymenthistory.worked_days_line_ids:
                        if worked_days_line_id.timetable_id.id:
                            end_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(worked_days_line_id.timetable_id.end_time, has_second=True)
                            start_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(worked_days_line_id.timetable_id.start_time, has_second=True)
                            key = '{}-{}-{}-{}'.format(worked_days_line_id.timetable_id.employee_id.id, worked_days_line_id.timetable_id.date, start_time, end_time)
                            if key not in key_payslips:
                                key_payslips[key] = {}
                                key_payslips[key]['timetable_id'] = worked_days_line_id.timetable_id.id
                                key_payslips[key]['rate'] = worked_days_line_id.rate
                                key_payslips[key]['amount'] = worked_days_line_id.amount
                                key_payslips[key]['number_of_hours'] = worked_days_line_id.number_of_hours
                        else:
                            end_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(worked_days_line_id.end_time, has_second=True)
                            start_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(worked_days_line_id.start_time, has_second=True)
                            key = '{}-{}-{}-{}'.format(worked_days_line_id.payslip_id.employee_id.id, worked_days_line_id.date, start_time, end_time)
                            if key not in key_payslips:
                                key_payslips[key] = {}
                                key_payslips[key]['timetable_id'] = None
                                key_payslips[key]['rate'] = worked_days_line_id.rate
                                key_payslips[key]['amount'] = worked_days_line_id.amount
                                key_payslips[key]['number_of_hours'] = worked_days_line_id.number_of_hours
                employee_ids.append(timetable.employee_id.id)

        timetable_ids = [payslip['timetable_id'] for payslip in key_payslips.values() if payslip['timetable_id']]

        if self.status:
            title.append(STATUS_ATTENDANCE[self.status])
            if self.status == 'paid':
                timetables = timetables.filtered(lambda rec: rec.id in timetable_ids)
            elif self.status == 'unpaid':
                timetables = timetables.filtered(lambda rec: rec.id not in timetable_ids)

        key_timetables = {}
        for timetable in timetables:
            if not timetable.date or not timetable.day_of_week or not timetable.employee_id.id:
                continue

            end_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(timetable.end_time, has_second=True)
            start_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(timetable.start_time, has_second=True)
            key = '{}-{}-{}-{}'.format(timetable.employee_id.id, timetable.date, start_time, end_time)
            if key in key_payslips and key_payslips[key]['timetable_id'] and key_payslips[key]['timetable_id'] != timetable.id:
                continue
            if key not in key_timetables:
                key_timetables[key] = timetable
            else:
                continue

            if timetable.status == 'present':
                end_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(timetable.worked_end_time, has_second=True)
                start_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(timetable.worked_start_time, has_second=True)
                end_time = datetime.strptime(f"{timetable.date} {end_time}", DATETIME_FORMAT)
                start_time = datetime.strptime(f"{timetable.date} {start_time}", DATETIME_FORMAT)

                worked_hours = end_time - start_time
                worked_hours = worked_hours.total_seconds() / 3600.0
                worked_hours = round(worked_hours, 2)
            elif timetable.status == 'permission':
                end_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(timetable.end_time, has_second=True)
                start_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(timetable.start_time, has_second=True)
                end_time = datetime.strptime(f"{timetable.date} {end_time}", DATETIME_FORMAT)
                start_time = datetime.strptime(f"{timetable.date} {start_time}", DATETIME_FORMAT)

                worked_hours = end_time - start_time
                worked_hours = worked_hours.total_seconds() / 3600.0
                worked_hours = round(worked_hours, 2)
            else:
                end_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(0.0, has_second=True)
                start_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(0.0, has_second=True)
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
                worked_hours = key_payslips[key]['number_of_hours']

            if not timetable.employee_id.is_permanent:
                if self.has_rate:
                    if rate == 0.0:
                        continue

            hours_credit = 0.0
            done = 0.0
            awaiting = 0.0
            worked_done = 0.0
            worked_awaiting = 0.0
            if timetable.class_group_id.id:
                key_class = '{}-{}'.format(timetable.class_id.id, timetable.class_group_id.id)
            else:
                key_class = '{}'.format(timetable.class_id.id)
            key_subject = '{}'.format(timetable.subject_id.id)
            if key_class in consumptionhours:
                if key_subject in consumptionhours[key_class]['data']:
                    hours_credit = consumptionhours[key_class]['data'][key_subject]['data']['hours_credit']
                    done = consumptionhours[key_class]['data'][key_subject]['data']['done']
                    awaiting = consumptionhours[key_class]['data'][key_subject]['data']['awaiting']
                    worked_done = consumptionhours[key_class]['data'][key_subject]['data']['worked_done']
                    worked_awaiting = consumptionhours[key_class]['data'][key_subject]['data']['worked_awaiting']

            if not timetable.employee_id.is_permanent:
                if self.refundable_additional:
                    if hours_credit >= worked_done:
                        continue

                original_worked_hours = 0.0
                original_worked_hours += worked_hours

                if self.refundable_additional or key not in key_payslips:
                    if worked_done > hours_credit:
                        if key_class not in key_extended_hours:
                            key_extended_hours[key_class] = {}
                            key_extended_hours[key_class][key_subject] = worked_done - hours_credit
                            key_extended_hours[key_class][key_subject] = round(key_extended_hours[key_class][key_subject], 2)
                        else:
                            if key_subject not in key_extended_hours[key_class]:
                                key_extended_hours[key_class][key_subject] = worked_done - hours_credit
                                key_extended_hours[key_class][key_subject] = round(key_extended_hours[key_class][key_subject], 2)
                        if self.refundable_additional:
                            if key_extended_hours[key_class][key_subject] == 0.0:
                                continue
                        if worked_hours > key_extended_hours[key_class][key_subject]:
                            if self.refundable_additional:
                                worked_hours = key_extended_hours[key_class][key_subject]
                                amount = rate * worked_hours
                                amount = round(amount, 2)
                            else:
                                worked_hours = worked_hours - key_extended_hours[key_class][key_subject]
                                worked_hours = round(worked_hours, 2)
                                amount = rate * worked_hours
                                amount = round(amount, 2)
                            key_extended_hours[key_class][key_subject] = 0.0
                        else:
                            key_extended_hours[key_class][key_subject] = key_extended_hours[key_class][key_subject] - worked_hours
                            key_extended_hours[key_class][key_subject] = round(key_extended_hours[key_class][key_subject], 2)
                            worked_hours = 0.0
                            amount = 0.0

                if self.refundable_additional:
                    if worked_hours == 0.0:
                        worked_hours = original_worked_hours
                        amount = rate * worked_hours
                        amount = round(amount, 2)

            teacher_timetable_attendance = self.env['teacher.timetable.attendance'].create({
                'timetable_id': timetable.id,
                'worked_time': worked_hours,
                'rate': rate,
                'amount': amount,
                'hours_credit': hours_credit,
                'done': done,
                'awaiting': awaiting,
                'worked_done': worked_done,
                'worked_awaiting': worked_awaiting,
                'status': timetable.status,
                'start_date': self.start_date,
                'end_date': self.end_date,
                'is_paid': True if timetable.id in timetable_ids else False,
                'is_refundable': True if self.refundable_additional else False,
                'sort_type': self.sort_type,
                'status_attendance': self.status,
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

    def consumptionhour(self, end_date=None):
        search_domain = []

        search_domain.append('|')
        search_domain.append('&')
        search_domain.append('&')
        search_domain.append(('group_id.is_active', '=', True))
        search_domain.append(('group_id.is_submit', '=', False))
        search_domain.append(('group_id.status', '=', 'valid'))
        search_domain.append('&')
        search_domain.append('&')
        search_domain.append('&')
        search_domain.append(('group_parent_id.is_active', '=', True))
        search_domain.append(('group_parent_id.is_submit', '=', False))
        search_domain.append(('group_parent_id.status', '=', 'valid'))
        search_domain.append(('group_id.status', '=', 'valid'))
        search_domain.append(('is_active', '=', True))
        search_domain.append(('status', 'in', ['present', 'permission']))

        search_domain.append(('employee_id.is_teacher', '=', True))

        order = 'date asc, id asc'

        search_consumptionhours = []

        consumptionhours = self.env['siantou.ems.timetable.timetable'].search(search_domain, order=order).sorted(lambda rec: (rec.date, rec.id))
        if end_date:
            consumptionhours = consumptionhours.filtered(lambda rec: rec.date and rec.day_of_week and rec.date <= end_date)
        consumptionhours = list(consumptionhours)
        key_consumptionhours = {}
        for consumptionhour in consumptionhours:
            if not consumptionhour.date or not consumptionhour.day_of_week or not consumptionhour.employee_id.id:
                continue

            end_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(consumptionhour.end_time, has_second=True)
            start_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(consumptionhour.start_time, has_second=True)
            if consumptionhour.class_group_id.id:
                key = '{}-{}-{}-{}-{}'.format(consumptionhour.class_id.id, consumptionhour.class_group_id.id, consumptionhour.date, start_time, end_time)
            else:
                key = '{}-{}-{}-{}'.format(consumptionhour.class_id.id, consumptionhour.date, start_time, end_time)
            if key not in key_consumptionhours:
                key_consumptionhours[key] = consumptionhour
            else:
                continue

            search_consumptionhours.append(consumptionhour)

        _logger.info(f'----------- tototototototo search_consumptionhours {search_consumptionhours} -----------')

        return search_consumptionhours

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
            if d['class_group_id']:
                key_class = '{}-{}'.format(d['class_id'], d['class_group_id'])
            else:
                key_class = '{}'.format(d['class_id'])
            key_subject = '{}'.format(d['subject_id'])
            if key_class not in consumptionhours:
                consumptionhours[key_class] = {}
                consumptionhours[key_class]['id'] = d['class_id']
                consumptionhours[key_class]['group_id'] = d['class_group_id']
                if d['class_group_id']:
                    consumptionhours[key_class]['name'] = '{} ({})'.format(d['class_name'], d['class_group_name'])
                else:
                    consumptionhours[key_class]['name'] = d['class_name']
                consumptionhours[key_class]['data'] = {}
                consumptionhours[key_class]['data'][key_subject] = {}
                consumptionhours[key_class]['data'][key_subject]['name'] = d['subject_name']
                consumptionhours[key_class]['data'][key_subject]['data'] = {
                    'hours_credit': 0.0,
                    'done': [],
                    'worked_done': [],
                }
                consumptionhours[key_class]['data'][key_subject]['data']['hours_credit'] = d['subject_hours_credit']
                consumptionhours[key_class]['data'][key_subject]['data']['done'].append(d)
                consumptionhours[key_class]['data'][key_subject]['data']['worked_done'].append(d)
            else:
                if key_subject not in consumptionhours[key_class]['data']:
                    consumptionhours[key_class]['data'][key_subject] = {}
                    consumptionhours[key_class]['data'][key_subject]['name'] = d['subject_name']
                    consumptionhours[key_class]['data'][key_subject]['data'] = {
                        'hours_credit': 0.0,
                        'done': [],
                        'worked_done': [],
                    }
                    consumptionhours[key_class]['data'][key_subject]['data']['hours_credit'] = d['subject_hours_credit']
                    consumptionhours[key_class]['data'][key_subject]['data']['done'].append(d)
                    consumptionhours[key_class]['data'][key_subject]['data']['worked_done'].append(d)
                else:
                    consumptionhours[key_class]['data'][key_subject]['data']['done'].append(d)
                    consumptionhours[key_class]['data'][key_subject]['data']['worked_done'].append(d)

        for key_class in consumptionhours.keys():
            consumptionhours[key_class]['hours_credit'] = 0.0
            consumptionhours[key_class]['total_done'] = 0.0
            consumptionhours[key_class]['total_awaiting'] = 0.0
            consumptionhours[key_class]['total_worked_done'] = 0.0
            consumptionhours[key_class]['total_worked_awaiting'] = 0.0
            for key_subject in consumptionhours[key_class]['data'].keys():
                consumptionhours[key_class]['data'][key_subject]['data']['done'] = sum([TeacherTimetableAttendanceFilterWizard.convert_number_of_hours(v) for v in consumptionhours[key_class]['data'][key_subject]['data']['done']])
                consumptionhours[key_class]['data'][key_subject]['data']['awaiting'] = consumptionhours[key_class]['data'][key_subject]['data']['hours_credit'] - consumptionhours[key_class]['data'][key_subject]['data']['done']
                consumptionhours[key_class]['data'][key_subject]['data']['worked_done'] = sum([TeacherTimetableAttendanceFilterWizard.convert_number_of_hours(v, worked_time=True) for v in consumptionhours[key_class]['data'][key_subject]['data']['worked_done']])
                consumptionhours[key_class]['data'][key_subject]['data']['worked_awaiting'] = consumptionhours[key_class]['data'][key_subject]['data']['hours_credit'] - consumptionhours[key_class]['data'][key_subject]['data']['worked_done']
                consumptionhours[key_class]['data'][key_subject]['data']['done'] = round(consumptionhours[key_class]['data'][key_subject]['data']['done'], 2)
                consumptionhours[key_class]['data'][key_subject]['data']['awaiting'] = round(consumptionhours[key_class]['data'][key_subject]['data']['awaiting'], 2)
                consumptionhours[key_class]['data'][key_subject]['data']['worked_done'] = round(consumptionhours[key_class]['data'][key_subject]['data']['worked_done'], 2)
                consumptionhours[key_class]['data'][key_subject]['data']['worked_awaiting'] = round(consumptionhours[key_class]['data'][key_subject]['data']['worked_awaiting'], 2)

                if consumptionhours[key_class]['data'][key_subject]['data']['awaiting'] < 0.0:
                    consumptionhours[key_class]['data'][key_subject]['data']['awaiting'] = 0.0

                if consumptionhours[key_class]['data'][key_subject]['data']['worked_awaiting'] < 0.0:
                    consumptionhours[key_class]['data'][key_subject]['data']['worked_awaiting'] = 0.0

                consumptionhours[key_class]['hours_credit'] += consumptionhours[key_class]['data'][key_subject]['data']['hours_credit']
                consumptionhours[key_class]['total_done'] += consumptionhours[key_class]['data'][key_subject]['data']['done']
                consumptionhours[key_class]['total_awaiting'] += consumptionhours[key_class]['data'][key_subject]['data']['awaiting']
                if consumptionhours[key_class]['data'][key_subject]['data']['worked_done'] > consumptionhours[key_class]['data'][key_subject]['data']['hours_credit']:
                    consumptionhours[key_class]['total_worked_done'] += consumptionhours[key_class]['data'][key_subject]['data']['hours_credit']
                else:
                    consumptionhours[key_class]['total_worked_done'] += consumptionhours[key_class]['data'][key_subject]['data']['worked_done']
                consumptionhours[key_class]['total_worked_awaiting'] += consumptionhours[key_class]['data'][key_subject]['data']['worked_awaiting']

        for key_class in consumptionhours.keys():
            consumptionhours[key_class]['hours_credit'] = round(consumptionhours[key_class]['hours_credit'], 2)
            consumptionhours[key_class]['total_done'] = round(consumptionhours[key_class]['total_done'], 2)
            consumptionhours[key_class]['total_awaiting'] = round(consumptionhours[key_class]['total_awaiting'], 2)
            consumptionhours[key_class]['total_worked_done'] = round(consumptionhours[key_class]['total_worked_done'], 2)
            consumptionhours[key_class]['total_worked_awaiting'] = round(consumptionhours[key_class]['total_worked_awaiting'], 2)

        _logger.info(f'----------- tototototototo consumptionhours {consumptionhours} -----------')

        return consumptionhours

    @staticmethod
    def convert_number_of_hours(tm, worked_time=False):
        if worked_time:
            end_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(tm['worked_end_time'], has_second=True)
            start_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(tm['worked_start_time'], has_second=True)
        else:
            end_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(tm['end_time'], has_second=True)
            start_time = TeacherTimetableAttendanceFilterWizard.convert_float_to_time(tm['start_time'], has_second=True)
        datetime_to = datetime.strptime(f"{tm['date']} {end_time}", DATETIME_FORMAT)
        datetime_from = datetime.strptime(f"{tm['date']} {start_time}", DATETIME_FORMAT)
        weekly_hours_credit = datetime_to - datetime_from

        weekly_hours_credit = weekly_hours_credit.total_seconds() / 3600.0
        weekly_hours_credit = round(weekly_hours_credit, 2)
        return weekly_hours_credit
