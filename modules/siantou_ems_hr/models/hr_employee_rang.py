# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Rang(models.Model):
    _name = "hr.employee.rang"
    _description = "Rang des employes"

    name = fields.Char(string="Libelé")
    code = fields.Char(string="Code")

