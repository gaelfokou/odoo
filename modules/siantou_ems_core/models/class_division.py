# -*- coding: utf-8 -*-
import logging

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo.tools import unique

class EducationClass(models.Model):
    _name = 'siantou.ems.core.class'
    _description = "Classe Standard"
    _inherit = ['mail.thread']
    
    
    _sql_constraints = [
        ('unique_class',
         'unique(filiere_id,niveau_id,speciality_id,school_id)',
         'Classe unique par school_id'),
    ]

    name = fields.Char(string='Nom', required=True,
                       help="Entrer le nom de la Classe")

    filiere_id = fields.Many2one('siantou.ems.core.field_of_study', string='Filière', required=True,
                                 help="Filière de la classe")
    niveau_id = fields.Many2one('siantou.ems.core.level', string='Niveau',required=True,
                                 help="Niveau de la classe")
    
    school_id = fields.Many2one('siantou.ems.core.school', string='Ecole')

    
    semestre_ids = fields.One2many(
        string='Semestre',
        comodel_name='siantou.ems.core.year.semester',
        inverse_name='class_id',
    )