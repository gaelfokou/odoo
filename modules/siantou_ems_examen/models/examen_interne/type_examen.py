# -*- coding: utf-8 -*-

from odoo import models, fields, api

class TypeExamen(models.Model):
    _name = 'siantou.ems.type.examen'
    _description = "Model pour gerer le type d'examen"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    code = fields.Char('Code', required=True, tracking=True)

    name = fields.Char('Nom', required=True, tracking=True)

