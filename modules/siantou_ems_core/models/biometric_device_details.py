# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BiometricDeviceDetails(models.Model):
    _inherit = 'biometric.device.details'

    building_ids = fields.Many2many('siantou.ems.core.building', 'device_building_rel', 'device_id', 'building_id', string="Bâtiments")
