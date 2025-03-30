# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, AccessError

class DegreeCourse(models.Model):
    _name = 'oe.school.course.degree'
    _description = 'Gestion des diplôme requis lors de la préinscription'
    _order = 'name'

    name = fields.Char(string='Nom', required=True, index=True, translate=True) 
    cursus_id = fields.Many2many(
        'oe.school.course',
        string='Cycle de la préinscription',
        required=True,
    )
