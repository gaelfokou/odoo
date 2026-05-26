from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from pprint import pformat
import pandas as pd
import numpy as np
import re
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import copy
import pytz
import logging

UTC_TZ = pytz.utc

DATE_FORMAT = '%Y-%m-%d'
DATE_FORMAT_FR = '%d/%m/%Y'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATETIME_FORMAT_FR = '%d/%m/%Y %H:%M'
TIME_FORMAT = '%H:%M:%S'
TIME_FORMAT_FR = '%H:%M'

METHOD_AUDIT_LOG = {
    'create': 'Create',
    'write': 'Write',
    'unlink': 'Unlink',
}

_logger = logging.getLogger(__name__)

class AuditLogFilterWizard(models.TransientModel):
    _name = 'audit.log.filter.wizard'
    _description = 'Filtrer les logs des utilisateurs'

    user_id = fields.Many2one(
        "res.users", "User"
    )

    model_id = fields.Many2one(
        "ir.model", "Model"
    )

    res_id = fields.Integer("Resource Id")

    method = fields.Selection([
        ('create', 'Create'),
        ('write', 'Write'),
        ('unlink', 'Unlink'),
    ], 'Method',
        # default='write',
    )

    start_date = fields.Datetime(
        'Date de début',
    )

    end_date = fields.Datetime(
        'Date de fin',
    )

    model_id_domain = fields.Binary(compute='_compute_model_domain', default=[])

    # Contrainte logique pour s'assurer que les dates de début et de fin sont définies et que la date de fin est supérieure à la date de début
    @api.constrains('start_date', 'end_date')
    def _constrains_date(self):
        for record in self:
            if record.start_date > record.end_date:
                raise ValidationError("La date de fin doit être supérieure ou égale à la date de début")

    @api.depends('model_id')
    def _compute_model_domain(self):
        for record in self:
            domain = [('active', '=', True)]
            model_ids = []
            audit_rule_ids = self.env['audit.rule'].sudo().search(domain)
            for audit_rule_id in audit_rule_ids:
                model_ids.append(audit_rule_id.model_id.id)
            model_ids = list(set(model_ids))
            domain = [
                ('id', 'in', model_ids)
            ]
            record.model_id_domain = domain

    @staticmethod
    def convert_datetime_from_utc(dt):
        new_tz = pytz.timezone('Africa/Douala')
        old_tz = pytz.utc
        local_dt = old_tz.localize(dt)
        dt = local_dt.astimezone(new_tz)
        return dt

    @staticmethod
    def convert_datetime_to_utc(dt):
        old_tz = pytz.timezone('Africa/Douala')
        new_tz = pytz.utc
        local_dt = old_tz.localize(dt)
        dt = local_dt.astimezone(new_tz)
        return dt

    def action_filter(self):
        domain = []
        title = []
        if self.user_id.id:
            domain.append(('user_id', '=', self.user_id.id))
            title.append(self.user_id.name)
        if self.model_id.id:
            domain.append(('model_id', '=', self.model_id.id))
            title.append(self.model_id.name)
        if self.res_id:
            domain.append(('res_id', '=', self.res_id))
            title.append(str(self.res_id))
        if self.method:
            domain.append(('method', '=', self.method))
            title.append(METHOD_AUDIT_LOG[self.method])

        audit_log_ids = []
        audit_logs = self.env['audit.log'].sudo().search(domain)
        if self.start_date and self.end_date:
            datetime_before = AuditLogFilterWizard.convert_datetime_from_utc(self.start_date)
            datetime_after = AuditLogFilterWizard.convert_datetime_from_utc(self.end_date)
            start_date = datetime.strftime(datetime_before, DATETIME_FORMAT_FR)
            end_date = datetime.strftime(datetime_after, DATETIME_FORMAT_FR)
            title.append('Date')
            title.append('{} - {}'.format(start_date, end_date))
            audit_logs = audit_logs.filtered(lambda rec: rec.create_date and rec.create_date >= self.start_date and rec.create_date <= self.end_date)
        for audit_log in audit_logs:
            audit_log_ids.append(audit_log.id)
        audit_log_ids = list(set(audit_log_ids))

        domain = [
            ('id', 'in', audit_log_ids)
        ]

        if len(title) > 0:
            title = ' / '.join(title)
        else:
            title = 'Non spécifié'

        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', title)

        tree_view = self.env.ref('smile_audit.view_audit_log_tree').id
        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'audit.log',
            'views': [(tree_view, 'tree'), (False, 'form')],
            'view_id': tree_view,
            'domain' : domain,
            'target': 'main',
        }
