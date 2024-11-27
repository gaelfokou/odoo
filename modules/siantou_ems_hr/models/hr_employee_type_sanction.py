# -*- coding: utf-8 -*-

from odoo import models, fields, api

class TypeSaction(models.Model):
    _name = "hr.employee.type.sanction"
    _description = "Model qui gère les type de sanction"

    name = fields.Char(string="Libellé")
    code = fields.Char(string="Code")

    type_sanction = fields.Selection([
        ("positive","Positive"),
        ("negative","Négative"),
        ("suspendu","Suspendre"),
        ("mis_a_pied","Mise à pied")
    ])