# -*- coding: utf-8 -*-
import logging
import re
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
                       compute='_compute_name', store=True,
                       help="Entrer le nom de la Classe")

    filiere_id = fields.Many2one('siantou.ems.core.field_of_study', string='Filière',
                                 help="Filière")

    student_ids = fields.One2many(
        'oe.school.student',
        'class_id',
        string='Liste des étudiants'
    )

    specialty_id = fields.Many2one('siantou.ems.core.specialty', string='Spécialité',
                                 help="Spécialité")

    option_id = fields.Many2one('siantou.ems.core.option', string='Option',
                                 help="Option")

    niveau_id = fields.Many2one('siantou.ems.core.level', string='Niveau',
                                 help="Niveau")
    
    school_id = fields.Many2one('siantou.ems.core.school', string='Ecole')
    
    annee_acadmique_id = fields.Many2one('siantou.ems.core.year', string='Année Académique')

    ue_ids = fields.One2many('siantou.ems.core.unite.enseignement', 'class_id', string='Unité d\'enseignement')

    type_cour = fields.Selection([
            ('cj', 'Cours du jour'),
            ('cs', 'Cours du soir'),
        ],
        string="Type de cours",
        default='cj',
    )

    group_ids = fields.One2many(
        'siantou.ems.core.class.group',
        'class_id',
        string='Liste des groupes'
    )

    @api.onchange('school_id')
    def _onchange_school(self):
        for record in self:
            record.filiere_id = None
            record.specialty_id = None
            record.option_id = None

    @api.onchange('filiere_id')
    def _onchange_filiere(self):
        for record in self:
            record.specialty_id = None
            record.option_id = None

    @api.onchange('specialty_id')
    def _onchange_specialty(self):
        for record in self:
            record.option_id = None

    @api.onchange('specialty_id', 'niveau_id', 'type_cour')
    def _onchange_name(self):
        for record in self:
            specialty_name = record.specialty_id.name if record.specialty_id.id else ''
            niveau_name = record.niveau_id.name if record.niveau_id.id else ''
            niveau_name = re.sub(r'Niveau ', '', niveau_name)
            type_cour_name = record.type_cour if record.type_cour == 'cs' else ''
            name = '{} {} {}'.format(specialty_name, niveau_name, type_cour_name)
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

    @api.depends('specialty_id', 'niveau_id', 'type_cour')
    def _compute_name(self):
        for record in self:
            specialty_name = record.specialty_id.name if record.specialty_id.id else ''
            niveau_name = record.niveau_id.name if record.niveau_id.id else ''
            niveau_name = re.sub(r'Niveau ', '', niveau_name)
            type_cour_name = record.type_cour if record.type_cour == 'cs' else ''
            name = '{} {} {}'.format(specialty_name, niveau_name, type_cour_name)
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

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
