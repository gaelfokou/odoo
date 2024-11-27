# -*- coding: utf-8 -*-

from odoo import models, fields, api


class EducationEquivalence(models.Model):
    _name = "hr.education.equivalence"
    _description = "Equivalence des diplômes"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(
        string="Libellé", 
        required=True)
    
    code = fields.Char(string='Code')
    
    active = fields.Boolean(
        string='Active ?',
        default=True)