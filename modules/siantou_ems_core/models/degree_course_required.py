# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, AccessError

class DegreeCourse(models.Model):
    _name = 'oe.school.course.degree'
    _description = 'Gestion des diplôme requis lors de la préinscription'
    _order = 'name'

    name = fields.Char(string='Nom', required=True) 
    cycle_ids = fields.Many2many('oe.school.course', 'course_degree_rel', 'diplo_requis_id', 'cycle_id', string='Cursus ou Cycles')
