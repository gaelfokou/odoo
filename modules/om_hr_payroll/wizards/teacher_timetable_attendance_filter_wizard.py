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
        end_date = (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()
        return start_date

    start_date = fields.Date(
        'Date de début',
        # required=True,
        default=_default_start_date,
    )

    def _default_end_date(self):
        end_date = (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()
        return end_date

    end_date = fields.Date(
        'Date de fin',
        # required=True,
        default=_default_end_date,
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

    def action_filter(self):
        self.env['teacher.timetable.attendance']._transient_vacuum()
        self.env['teacher.timetable.attendance'].search([]).unlink()

        domain = []
        title = []
        if self.employee_id.id:
            domain.append(('employee_id', '=', self.employee_id.id))
            title.append(self.employee_id.name)
        if self.status:
            domain.append(('status', '=', self.status))
            title.append(STATUS_TIMETABLE[self.status])
        if self.is_permanent:
            title.append('Est un permanent')

        domain.append(('group_id.is_active', '=', True))
        domain.append(('group_id.is_submit', '=', False))
        domain.append(('employee_id.is_permanent', '=', self.is_permanent))

        timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
        if self.start_date and self.end_date:
            start_date = datetime.strftime(self.start_date, DATE_FORMAT_FR)
            end_date = datetime.strftime(self.end_date, DATE_FORMAT_FR)
            title.append('{} - {}'.format(start_date, end_date))
            timetables = timetables.filtered(lambda rec: rec.date and rec.date >= self.start_date and rec.date <= self.end_date)

        key_timetables = {}
        for timetable in timetables:
            if timetable.status == 'present':
                end_time = datetime.strptime(f"{timetable.date} {TeacherTimetableAttendanceFilterWizard.convert_float_to_time(timetable.worked_end_time, True)}", DATETIME_FORMAT)
                start_time = datetime.strptime(f"{timetable.date} {TeacherTimetableAttendanceFilterWizard.convert_float_to_time(timetable.worked_start_time, True)}", DATETIME_FORMAT)

                key = '{}-{}-{}-{}'.format(timetable.employee_id.id, timetable.date, start_time, end_time)
                if not key in key_timetables:
                    key_timetables[key] = timetable
                else:
                    continue

                worked_hours = end_time - start_time
                worked_hours = worked_hours.total_seconds() / 3600.0
                worked_hours = round(worked_hours, 2)
            elif timetable.status == 'permission':
                end_time = datetime.strptime(f"{timetable.date} {TeacherTimetableAttendanceFilterWizard.convert_float_to_time(timetable.end_time, True)}", DATETIME_FORMAT)
                start_time = datetime.strptime(f"{timetable.date} {TeacherTimetableAttendanceFilterWizard.convert_float_to_time(timetable.start_time, True)}", DATETIME_FORMAT)

                key = '{}-{}-{}-{}'.format(timetable.employee_id.id, timetable.date, start_time, end_time)
                if not key in key_timetables:
                    key_timetables[key] = timetable
                else:
                    continue

                worked_hours = end_time - start_time
                worked_hours = worked_hours.total_seconds() / 3600.0
                worked_hours = round(worked_hours, 2)
            else:
                end_time = datetime.strptime(f"{timetable.date} {TeacherTimetableAttendanceFilterWizard.convert_float_to_time(0.0, True)}", DATETIME_FORMAT)
                start_time = datetime.strptime(f"{timetable.date} {TeacherTimetableAttendanceFilterWizard.convert_float_to_time(0.0, True)}", DATETIME_FORMAT)

                key = '{}-{}-{}-{}'.format(timetable.employee_id.id, timetable.date, start_time, end_time)
                if not key in key_timetables:
                    key_timetables[key] = timetable
                else:
                    continue

                worked_hours = end_time - start_time
                worked_hours = worked_hours.total_seconds() / 3600.0
                worked_hours = round(worked_hours, 2)

            domain = [
                ('school_id', '=', timetable.school_id.id),
                ('cycle_id', '=', timetable.cycle_id.id),
                ('level_id', '=', timetable.level_id.id),
                # ('diplome_availability_id.diplome_ids', 'in', timetable.employee_id.diplome_ids.ids),
            ]

            hourly_rates = self.env['siantou.ems.core.hourly.rate'].search(domain)
            hourly_rates = list(hourly_rates)

            rate = None
            if len(hourly_rates) > 0:
                for hourly_rate in hourly_rates:
                    domain = [
                        ('hourly_rate_id', '=', hourly_rate.id),
                        ('employee_id', '=', timetable.employee_id.id),
                        ('subject_id', '=', timetable.subject_id.id),
                    ]

                    teacher_hourly_rate = self.env['siantou.ems.core.teacher.hourly.rate'].search(domain, limit=1)
                    if teacher_hourly_rate:
                        rate = teacher_hourly_rate.rate
                        break
                if not rate:
                    rate = hourly_rates[0].rate

            if not rate:
                rate = 0.0

            amount = rate * worked_hours
            amount = round(amount, 2)

            teacher_timetable_attendance = self.env['teacher.timetable.attendance'].create({
                'timetable_id': timetable.id,
                'worked_time': worked_hours,
                'rate': rate,
                'amount': amount,
            })

        if len(title) > 0:
            title = '/'.join(title)
        else:
            title = 'Non spécifié'

        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', title)

        view_id = self.env.ref('siantou_ems_core.timetable_tree_view').id
        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
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
