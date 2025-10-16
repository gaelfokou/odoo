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
    _description = 'Filtre des émargements d\'enseignant'

    # Enseignant lié à la programmation de cours
    employee_id = fields.Many2one(
        'hr.employee',
        'Enseignant',
        required=True,
    )

    start_date = fields.Date(
        'Date de début',
        required=True,
    )

    end_date = fields.Date(
        'Date de fin',
        required=True,
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
        domain = []
        title = []
        if self.employee_id.id:
            domain.append(('employee_id', '=', self.employee_id.id))
            title.append(self.employee_id.name)
        if self.status:
            domain.append(('status', '=', self.status))
            title.append(STATUS_TIMETABLE[self.status])

        timetable_ids = []
        timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
        if self.start_date and self.end_date:
            start_date = datetime.strftime(self.start_date, DATE_FORMAT_FR)
            end_date = datetime.strftime(self.end_date, DATE_FORMAT_FR)
            title.append('{} - {}'.format(start_date, end_date))
            timetables = timetables.filtered(lambda rec: rec.date >= self.start_date and rec.date <= self.end_date)
        for timetable in timetables:
            timetable_ids.append(timetable.id)
        timetable_ids = list(set(timetable_ids))

        domain = [
            ('id', 'in', timetable_ids)
        ]

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
            'domain' : domain,
            'target': 'main',
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

class TeacherTimetableAttendance(models.TransientModel):
    _name = 'teacher.timetable.attendance'
    _description = 'Émargement d\'enseignant'

    timetable_id = fields.Many2one(
        'siantou.ems.timetable.timetable',
        string='Emploi du temps',
        required=True,
    )

    class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe',
        related='timetable_id.class_id',
        store=True
    )

    subject_id = fields.Many2one(
        'siantou.ems.core.subject',
        'Cours',
        related='timetable_id.subject_id',
        store=True
    )

    # Enseignant lié à la programmation de cours
    employee_id = fields.Many2one(
        'hr.employee',
        'Enseignant',
        related='timetable_id.employee_id',
        store=True
    )

    date = fields.Date(
        'Date',
        related='timetable_id.date',
        store=True
    )

    # Heure de début du cours
    start_time = fields.Float(
        'Heure de début',
        related='timetable_id.start_time',
        store=True
    )

    # Heure de fin du cours
    end_time = fields.Float(
        'Heure de fin',
        related='timetable_id.end_time',
        store=True
    )

    # Heure de début du cours
    worked_start_time = fields.Float(
        'Heure de début effectuée',
        default=0.0,
        widget='time'
    )

    # Heure de fin du cours
    worked_end_time = fields.Float(
        'Heure de fin effectuée',
        default=0.0,
        widget='time'
    )

    # Heure de fin du cours
    worked_time = fields.Float(
        'Heure effectuée',
        default=0.0,
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

    # Taux de l\'enseignant
    rate = fields.Float(
        'Taux horaire',
        default=0.0,
    )

    amount = fields.Float()

    # Contrainte logique pour s'assurer que les heures de début et de fin sont définies et que l'heure de fin est supérieure à l'heure de début
    @api.constrains('start_time', 'end_time')
    def _constrains_time(self):
        for record in self:
            if record.end_time < record.start_time:
                raise ValidationError("L'heure de fin du cours doit être supérieure à l'heure de début du cours")

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
