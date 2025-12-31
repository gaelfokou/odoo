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

STATUS_CLASSROOM = {
    'available': 'Disponible',
    'not_available': 'Pas disponible',
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
        default=0.0,
        widget='time'
    )

    # Heure de fin du cours
    end_time = fields.Float(
        'Heure de fin',
        default=0.0,
        widget='time'
    )

    status = fields.Selection([
        ('available', 'Disponible'),
        ('not_available', 'Pas disponible'),
    ], 'Statut',
        # default='available',
    )

    # Contrainte logique pour s'assurer que les heures de début et de fin sont définies et que l'heure de fin est supérieure à l'heure de début
    @api.constrains('start_time', 'end_time')
    def _constrains_time(self):
        for record in self:
            if record.start_time < 0.0 or record.end_time < 0.0 or record.start_time > 23.59 or record.end_time > 23.59:
                raise ValidationError("Vous devez définir des heures de début et de fin corrects")
            elif record.start_time > record.end_time:
                raise ValidationError("L'heure de fin du cours doit être supérieure à l'heure de début du cours")

    def action_filter(self):
        domain = [
            '|',
            '&',
            ('group_id.is_active', '=', True),
            ('group_id.is_submit', '=', False),
            '&',
            ('group_parent_id.is_active', '=', True),
            ('group_parent_id.is_submit', '=', False),
        ]
        title = []
        if self.date:
            domain.append(('date', '=', self.date))
            title.append(datetime.strftime(self.date, DATE_FORMAT_FR))

        classroom_ids = []
        timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
        if self.start_time and self.end_time:
            start_time = ClassroomFilterWizard.convert_float_to_time(self.start_time)
            end_time = ClassroomFilterWizard.convert_float_to_time(self.end_time)
            title.append('{} - {}'.format(start_time, end_time))
            timetables = timetables.filtered(lambda rec: not (rec.start_time >= self.end_time or rec.end_time <= self.start_time))
        for timetable in timetables:
            classroom_ids.append(timetable.classroom_id.id)
        classroom_ids = list(set(classroom_ids))

        if self.status:
            if self.status == 'available':
                domain = [
                    ('id', 'not in', classroom_ids),
                ]
                title.append(STATUS_CLASSROOM[self.status])
            elif self.status == 'not_available':
                domain = [
                    ('id', 'in', classroom_ids),
                ]
                title.append(STATUS_CLASSROOM[self.status])

        if len(title) > 0:
            title = ' / '.join(title)
        else:
            title = 'Non spécifié'

        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', title)

        view_id = self.env.ref('siantou_ems_core.classroom_tree_view').id
        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'siantou.ems.core.building.classroom',
            'views': [(view_id, 'tree'), (False, 'form')],
            'view_id': view_id,
            'domain' : domain,
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
