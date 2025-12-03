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

OPERATION_TYPE_USER_AUDIT = {
    'read': 'Read',
    'write': 'Write',
    'create': 'Create',
    'delete': 'Delete',
}

_logger = logging.getLogger(__name__)

class UserAuditFilterWizard(models.TransientModel):
    _name = 'user.audit.filter.wizard'
    _description = 'Filtrer les logs des utilisateurs'

    user_id = fields.Many2one('res.users', string="User",
                                help="Manage users")

    model_id = fields.Many2one('ir.model', string="Model",
                                 help='Used to select which model is to track')

    record = fields.Integer(string="Record ID",
                            help="For getting which record has accessed")

    operation_type = fields.Selection(selection=[('read', 'Read'),
                                                 ('write', 'Write'),
                                                 ('create', 'Create'),
                                                 ('delete', 'Delete')],
                                      string="Type",
                                      help="For getting which operation has "
                                           "been performed")

    start_date = fields.Datetime(
        'Date de début',
    )

    end_date = fields.Datetime(
        'Date de fin',
    )

    user_id_domain = fields.Binary(compute='_compute_user_domain', default=[])

    model_id_domain = fields.Binary(compute='_compute_model_domain', default=[])

    # Contrainte logique pour s'assurer que les dates de début et de fin sont définies et que la date de fin est supérieure à la date de début
    @api.constrains('start_date', 'end_date')
    def _constrains_date(self):
        for record in self:
            if record.start_date > record.end_date:
                raise ValidationError("La date de fin doit être supérieure à la date de début")

    @api.depends('user_id')
    def _compute_user_domain(self):
        for record in self:
            user_ids = []
            user_audit_ids = self.env['user.audit'].sudo().search([])
            for user_audit_id in user_audit_ids:
                for user_id in user_audit_id.user_ids:
                    user_ids.append(user_id.id)
            user_ids = list(set(user_ids))
            domain = [
                ('id', 'in', user_ids)
            ]
            record.user_id_domain = domain

    @api.depends('model_id')
    def _compute_model_domain(self):
        for record in self:
            model_ids = []
            user_audit_ids = self.env['user.audit'].sudo().search([])
            for user_audit_id in user_audit_ids:
                for model_id in user_audit_id.model_ids:
                    model_ids.append(model_id.id)
            model_ids = list(set(model_ids))
            domain = [
                ('id', 'in', model_ids)
            ]
            record.model_id_domain = domain

    def action_filter(self):
        domain = []
        title = []
        if self.user_id.id:
            domain.append(('user_id', '=', self.user_id.id))
            title.append(self.user_id.name)
        if self.model_id.id:
            domain.append(('model_id', '=', self.model_id.id))
            title.append(self.model_id.name)
        if self.record:
            domain.append(('record', '=', self.record))
            title.append(str(self.record))
        if self.operation_type:
            domain.append(('operation_type', '=', self.operation_type))
            title.append(OPERATION_TYPE_USER_AUDIT[self.operation_type])

        user_audit_log_ids = []
        user_audit_logs = self.env['user.audit.log'].sudo().search(domain)
        if self.start_date and self.end_date:
            start_date = datetime.strftime(self.start_date, DATE_FORMAT_FR)
            end_date = datetime.strftime(self.end_date, DATE_FORMAT_FR)
            title.append('{} - {}'.format(start_date, end_date))
            user_audit_logs = user_audit_logs.filtered(lambda rec: rec.date and rec.date >= self.start_date and rec.date <= self.end_date)
        for user_audit_log in user_audit_logs:
            user_audit_log_ids.append(user_audit_log.id)
        user_audit_log_ids = list(set(user_audit_log_ids))

        domain = [
            ('id', 'in', user_audit_log_ids)
        ]

        if len(title) > 0:
            title = '/'.join(title)
        else:
            title = 'Non spécifié'

        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', title)

        tree_view = self.env.ref('user_audit.user_audit_log_view_tree').id
        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form,kanban',
            'res_model': 'user.audit.log',
            'views': [(tree_view, 'tree'), (False, 'form'), (False, 'kanban')],
            'view_id': tree_view,
            'domain' : domain,
            'target': 'main',
        }
