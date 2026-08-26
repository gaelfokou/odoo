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
import base64
import os
from odoo.tools.misc import file_path
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


class GeneralSetting(models.Model):
    _name = 'siantou.ems.core.general.setting'
    _description = 'Paramètre général'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    name = fields.Char(
        string='Nom',
        required=True,
        translate=True,
    )

    description = fields.Text(
        'Description',
    )

    file = fields.Binary(
        string='Logo',
        attachment=True
    )

    file_name = fields.Char(
        string='Nom du logo'
    )

    file_path = fields.Char(
        string='Chemin d\'accès du logo',
        compute='_compute_path',
        store=True,
    )

    @api.depends('file', 'file_name')
    def _compute_path(self):
        for record in self:
            if record.file_name:
                try:
                    image_path = file_path(file_path=f'siantou_ems_core/static/src/img/{record.file_name}', filter_ext=('.png', '.jpg', '.jpeg'), env=self.env)
                    record.file_path = f'siantou_ems_core/static/src/img/{record.file_name}'
                except FileNotFoundError:
                    module_path = os.path.dirname(os.path.realpath(__file__))
                    module_path = module_path.replace('/models', '')
                    module_path = module_path.replace('\\models', '')
                    image_path = os.path.join(module_path, 'static', 'src', 'img', record.file_name)
                    file_bytes = base64.b64decode(record.file)
                    with open(image_path, 'wb') as f:
                        f.write(file_bytes)
                        record.file_path = f'siantou_ems_core/static/src/img/{record.file_name}'
            else:
                record.file_path = None

    @api.onchange('file', 'file_name')
    def _onchange_path(self):
        for record in self:
            record._compute_path()

    @api.constrains('file', 'file_name')
    def _check_file(self):
        for record in self:
            if record.file_name:
                file_name = record.file_name
                file_name = file_name.lower()
                if file_name.split('.')[-1] not in ['png', 'jpg', 'jpeg']:
                        raise ValidationError('Impossible de télécharger un fichier différent de .png, .jpg, .jpeg')
