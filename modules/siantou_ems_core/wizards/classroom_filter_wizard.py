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
            if record.end_time < record.start_time:
                raise ValidationError("L'heure de fin du cours doit être supérieure à l'heure de début du cours")

    def action_filter(self):
        domain = []
        title = []
        if self.date:
            domain.append(('date', '=', self.date))

        classroom_ids = []
        if self.start_time and self.end_time:
            timetables = self.env['siantou.ems.timetable.timetable'].search(domain).filtered(lambda rec: not (rec.start_time >= self.end_time or rec.end_time <= self.start_time))
        else:
            timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
        for timetable in timetables:
            classroom_ids.append(timetable.classroom_id.id)
        classroom_ids = list(set(classroom_ids))

        if self.status == '0':
            domain = [
                ('id', 'not in', classroom_ids),
            ]
            title.append('Disponible')
        elif self.status == '1':
            domain = [
                ('id', 'in', classroom_ids),
            ]
            title.append('Pas disponible')

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
