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

class ClassroomFilterWizard(models.TransientModel):
    _name = 'classroom.filter.wizard'
    _description = 'Filtre des salles de classe'

    date = fields.Date(
        'Date du jour',
    )

    # Heure de début du cours
    start_time = fields.Float(
        'Heure de début',
        default=0,
        widget='time'
    )

    # Heure de fin du cours
    end_time = fields.Float(
        'Heure de fin',
        default=0,
        widget='time'
    )

    status = fields.Selection([
        ('0', 'Disponible'),
        ('1', 'Pas disponible'),
    ], 'Statut',
        default='0',
    )

    # Contrainte logique pour s'assurer que les heures de début et de fin sont définies et que l'heure de fin est supérieure à l'heure de début
    @api.constrains('start_time', 'end_time')
    def _constrains_time(self):
        for record in self:
            if record.start_time <= 0.0 or record.end_time <= 0.0:
                raise ValidationError("Vous devez définir des heures de début et de fin corrects")
            elif record.end_time <= record.start_time:
                raise ValidationError("L'heure de fin du cours doit être supérieure à l'heure de début du cours")

    def action_filter(self):
        domain = []
        title = []
        if self.date:
            domain.append(('date', '=', self.date))
        if self.start_time and self.end_time:
            domain.append(('end_time', '>=', self.start_time))
            domain.append(('start_time', '<=', self.end_time))
        if self.status:
            domain.append(('status', '=', self.status))

        if len(title) > 0:
            title = '/'.join(title)
        else:
            title = 'Salles de classe filtrées'

        self.env['ir.config_parameter'].set_param(f'filter.{self.env.user.id}', title)

        view_id = self.env.ref('siantou_ems_core.classroom_tree_view').id
        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'siantou.ems.core.building.classroom',
            'views': [(view_id, 'tree')],
            'view_id': view_id,
            'domain' : domain,
            'target': 'main',
        }
