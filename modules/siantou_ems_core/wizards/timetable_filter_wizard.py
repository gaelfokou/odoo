import logging

from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
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
class TimetableFilterWizard(models.TransientModel):
    _name = 'siantou.ems.timetable.timetable_filter_wizard'
    _description = 'Filtre de l\'emploi du temps'

    # Semestre pour lequel on souhaite tirer l'emploi du temps
    semester_id = fields.Many2one(
        'siantou.ems.core.year.semester',
        string='Semestre',
        related='group_id.semester_id',
        store=True
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

    # Niveau lié à la programmation de cours
    level_id = fields.Many2one(
        'siantou.ems.core.level',
        'Niveau',
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

    @api.constrains('period_from', 'period_to')
    def _check_constrains_period(self):
        for record in self:
            if record.period_from and record.period_to:
                if record.period_from > record.period_to:
                    raise ValidationError(f"La période de début ne doit pas être supérieure à la période de fin")
                elif record.period_from + relativedelta(months=1) < record.period_to:
                    raise ValidationError(f"La plage entre la période de début et la période de fin ne doit pas être supérieure 1 mois")

    def action_timetable_filter(self):
        action = self.env.ref('siantou_ems_core.action_show_timetable').read()[0]
        action.update({
            'name': 'Emploi du temps',
            'res_model': 'siantou.ems.timetable.timetable',
            'type': 'ir.actions.act_window',
        })
        return action
