# -*- coding: utf-8 -*-
import logging

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo.tools import unique

class EducationClass(models.Model):
    _name = 'siantou.ems.core.class'
    _description = "Classe Standard"
    _inherit = ['mail.thread']
    
    
    # _sql_constraints = [
    #     ('unique_class',
    #      'unique(filiere_id,niveau_id,school_id)',
    #      'Classe unique par school_id'),
    # ]

    name = fields.Char(string='Nom', required=True,
                       help="Entrer le nom de la Classe")

    filiere_id = fields.Many2one('siantou.ems.core.field_of_study', string='Filière', required=True,
                                 help="Filière")

    student_ids = fields.One2many(
        'oe.school.student',
        'field_of_study_id',
        string='Liste des étudiants'
    )

    specialty_id = fields.Many2one('siantou.ems.core.specialty', string='Spécialité', required=True,
                                 help="Spécialité")

    niveau_id = fields.Many2one('siantou.ems.core.level', string='Niveau', required=True,
                                 help="Niveau")
    
    school_id = fields.Many2one('siantou.ems.core.school', string='Ecole')
    
    annee_acadmique_id = fields.Many2one('siantou.ems.core.year', string='Année Académique')

    ue_ids = fields.One2many(comodel_name='siantou.ems.core.unite.enseignement', inverse_name='class_id', string='Unité d\'enseignement')

    type_cour = fields.Selection([
            ('cj', 'Cours du jour'),
            ('cs', 'Cours du soir'),
        ],
        string="Type de cours",
        required=True,
        default='cj',
    )

    group_ids = fields.One2many(
        'siantou.ems.core.class.group',
        'class_id',
        string='Liste des groupes'
    )

class EducationClassGroup(models.Model):
    _name = 'siantou.ems.core.class.group'
    _description = "Groupe de classe"

    name = fields.Char(string='Nom', required=True,
                       help="Entrer le nom du groupe")

    class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe',
        ondelete='cascade'
    )
