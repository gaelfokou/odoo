# -*- coding:utf-8 -*-

from datetime import date

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError


class LicencierEmployee(models.Model):
    _name = "hr.motif.licenciement"
    _description = "Model pour gérer les motifs de licenciement"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    code = fields.Char("Code")

    name = fields.Char(string='Nom')
