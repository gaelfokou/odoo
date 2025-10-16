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
