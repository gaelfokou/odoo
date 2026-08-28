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
# from odoo.tools.misc import file_path
import logging

_logger = logging.getLogger(__name__)


class GeneralSetting(models.Model):
    _name = 'siantou.ems.core.general.setting'
    _description = 'Paramètre général'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    name = fields.Char(
        string='Nom',
        compute='_compute_name',
        store=True,
    )

    year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année académique',
    )

    title = fields.Char(
        string='Titre',
        required=True,
        translate=True,
    )

    description = fields.Text(
        'Description',
        translate=True,
    )

    phone = fields.Char(
        string='Numéro de téléphone',
    )

    email = fields.Char(
        string='E-mail',
    )

    site = fields.Char(
        string='Site web',
    )

    file = fields.Binary(
        string='Logo',
        required=True,
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

    _sql_constraints = [
        ('unique_year_id', 'unique(year_id)', 'L\'année académique doit être unique.'),
    ]

    @api.depends('title')
    def _compute_name(self):
        for record in self:
            record.name = record.title if record.title else ''

    @api.onchange('title')
    def _onchange_name(self):
        for record in self:
            record._compute_name()

    @api.depends('file', 'file_name')
    def _compute_path(self):
        for record in self:
            if record.file_name:
                module_path = os.path.dirname(os.path.realpath(__file__))
                module_path = os.path.dirname(module_path)
                directory_path = os.path.join(module_path, 'static', 'src', 'img', 'upload')
                if not os.path.exists(directory_path):
                    os.mkdir(directory_path)
                file_path = os.path.join(module_path, 'static', 'src', 'img', 'upload', record.file_name)
                relative_path = f'/siantou_ems_core/static/src/img/{record.file_name}'
                if os.path.exists(file_path):
                    _logger.info(f'----------- tototototototo file_path exists {file_path} -----------')
                else:
                    file_bytes = base64.b64decode(record.file)
                    with open(file_path, 'wb') as f:
                        f.write(file_bytes)
                    _logger.info(f'----------- tototototototo file_path not exists {file_path} -----------')
                record.file_path = relative_path
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

    def write(self, vals):
        settings = []
        if len(self.ids) == 1:
            setting = self.env['siantou.ems.core.general.setting'].browse(self.id)
            settings.append(setting)
        else:
            settings = self.env['siantou.ems.core.general.setting'].browse(self.ids)
            settings = list(settings)

        if 'file_name' in vals:
            for setting in settings:
                if setting.file_name and setting.file_name != vals['file_name']:
                    module_path = os.path.dirname(os.path.realpath(__file__))
                    module_path = os.path.dirname(module_path)
                    file_path = os.path.join(module_path, 'static', 'src', 'img', 'upload', setting.file_name)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        _logger.info(f'----------- tototototototo remove file_path exists {file_path} -----------')
                    else:
                        _logger.info(f'----------- tototototototo remove file_path not exists {file_path} -----------')

        res = super(GeneralSetting, self).write(vals)

        return res

    def unlink(self):
        settings = []
        if len(self.ids) == 1:
            setting = self.env['siantou.ems.core.general.setting'].browse(self.id)
            settings.append(setting)
        else:
            settings = self.env['siantou.ems.core.general.setting'].browse(self.ids)
            settings = list(settings)

        for setting in settings:
            if setting.file_name:
                module_path = os.path.dirname(os.path.realpath(__file__))
                module_path = os.path.dirname(module_path)
                file_path = os.path.join(module_path, 'static', 'src', 'img', 'upload', setting.file_name)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    _logger.info(f'----------- tototototototo remove file_path exists {file_path} -----------')
                else:
                    _logger.info(f'----------- tototototototo remove file_path not exists {file_path} -----------')

        setting = super(GeneralSetting, self).unlink()

        return setting
