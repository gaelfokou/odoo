# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP
from datetime import date, datetime, timedelta, time
import random
import re
import psycopg2
import copy
import logging

_logger = logging.getLogger(__name__)

DATE_FORMAT = '%Y-%m-%d'
DATE_FORMAT_FR = '%d/%m/%Y'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATETIME_FORMAT_FR = '%d/%m/%Y %H:%M'
TIME_FORMAT = '%H:%M:%S'
TIME_FORMAT_FR = '%H:%M'

TYPE_TRACKREQUEST = {
    'academic_information': 'Informations académiques',
    'exam_score': 'Notes d\'examen',
}

STATUS_TRACKREQUEST = {
    'pending': 'En attente',
    'progress': 'En cours',
    'rejected': 'Rejeté',
    'done': 'Traité',
}

class RequestTrack(models.Model):
    _name = 'siantou.ems.core.request.track'
    _description = 'Requête'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    name = fields.Char(
        string='Nom',
    )

    description = fields.Text(
        'Description',
    )

    file = fields.Binary(
        string='Fichier'
    )

    file_name = fields.Char(
        string='Nom du fichier'
    )

    @api.constrains('file', 'file_name')
    def _check_file(self):
        for record in self:
            if record.file_name:
                file_name = record.file_name
                file_name = file_name.lower()
                if file_name.split('.')[-1] not in ['pdf', 'doc', 'docx', 'xls', 'xlsx']:
                        raise ValidationError('Impossible de télécharger un fichier différent de .pdf, .doc, .docx, .xls, .xlsx')

    note = fields.Text(
        'Remarque',
    )

    type_request = fields.Selection([
        ('academic_information', 'Informations académiques'),
        ('exam_score', 'Notes d\'examen'),
    ], 'Type de requête',
        default='academic_information',
    )

    status = fields.Selection([
        ('pending', 'En attente'),
        ('progress', 'En cours'),
        ('rejected', 'Rejeté'),
        ('done', 'Traité'),
    ], 'Statut',
        default='pending',
    )

    state = fields.Selection([
        ('pending', 'En attente'),
        ('progress', 'En cours'),
        ('rejected', 'Rejeté'),
        ('done', 'Traité'),
    ],
        string='Statut',
        related='status',
        store=True,
        tracking=True
    )

    def _default_date(self):
        return date.today()

    date = fields.Date(
        string='Date limite',
        default=_default_date,
    )

    user_ids = fields.Many2many(
        'res.users',
        'read_user_request_rel',
        'request_id',
        'user_id',
        string='Utilisateurs assignés',
    )

    def state_pending_request(self):
        self.write({
            'status': 'pending',
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def state_progress_request(self):
        self.write({
            'status': 'progress',
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def state_rejected_request(self):
        self.write({
            'status': 'rejected',
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def state_done_request(self):
        self.write({
            'status': 'done',
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
