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


class TimetableTypeError(models.Model):
    _name = 'data.copy.type'
    _description = 'Type de copie des données'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    name = fields.Char(
        string='Nom',
        compute='_compute_name',
        store=True,
    )

    model_id = fields.Many2one(
        'ir.model',
        string='Model',
    )

    _sql_constraints = [
        ('unique_model', 'unique(model_id)', 'Le modèle doit être unique.'),
    ]

    @api.depends('model_id')
    def _compute_name(self):
        for record in self:
            record.name = record.model_id.name

    @api.onchange('model_id')
    def _onchange_name(self):
        for record in self:
            record._compute_name()


class DataCopyWizard(models.TransientModel):
    _name = 'data.copy.wizard'
    _description = 'Copie des autres données'

    def _default_year(self):
            year = self.env['siantou.ems.core.year'].sudo().search([
                ('active_user_ids', '=', self.env.user.id),
            ], limit=1)
            if not year:
                year = self.env['siantou.ems.core.year'].sudo().search([('is_active', '=', True)], limit=1)
            return year

    source_year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année académique source',
        default=_default_year,
        required=True
    )

    destination_year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année académique destination',
        required=True,
    )

    type_id = fields.Many2one(
        'data.copy.type',
        string='Type de copie des données',
        required=True,
    )

    def action_copy(self):
        domain = []
        if self.type_id:
            domain.append(('id', '=', self.type_id.model_id.id))

        model_id = self.env['ir.model'].sudo().search(domain, limit=1)

        _logger.info(f'----------- tototototototo model {model_id.model} -----------')

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
