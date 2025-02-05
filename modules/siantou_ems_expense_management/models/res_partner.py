# -*- coding: utf-8 -*-
from odoo import models, fields, api,  _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    prestataire = fields.Boolean(string='Prestataire', default=False, copy=True)