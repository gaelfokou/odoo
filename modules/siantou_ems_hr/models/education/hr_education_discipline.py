# -*- coding: utf-8 -*-

from odoo import models, fields, api


class EducationDiscipline(models.Model):
    _name = "hr.education.discipline"
    _description = "Discipline des diplômes"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(
        string="Libellé", 
        required=True)
    
    code = fields.Char(string='Code')
    
    active = fields.Boolean(
        string='Active ?',
        default=True)