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
         'unique(filiere_id,niveau_id,school_id)',
         'Classe unique par school_id'),
    ]

    name = fields.Char(string='Nom', required=True,
                       help="Entrer le nom de la Classe")

    filiere_id = fields.Many2one('siantou.ems.core.field_of_study', string='Filière', required=True,
                                 help="Filière")
    
    specialty_ids = fields.Many2many('siantou.ems.core.specialty', string='Liste des spécialités')
    
    niveau_id = fields.Many2one('siantou.ems.core.level', string='Niveau',required=True,
                                 help="Niveau")
    
    school_id = fields.Many2one('siantou.ems.core.school', string='Ecole')
    
    annee_acadmique_id = fields.Many2one('siantou.ems.core.year', string='Année Académique')
    
    semestre_id = fields.Many2one('siantou.ems.core.year.semester', string='Semestre', tracking=True)
    
    
    ue_ids = fields.One2many(comodel_name='siantou.ems.core.unite.enseignement', inverse_name='class_id', string='Unité d\'enseignement')
    
    
    @api.onchange('filiere_id')
    def _onchange_filiere_id(self):
        if self.filiere_id:
            # Récupérer les specialty_ids associées à l'école sélectionnée
            specialty = self.env['siantou.ems.core.specialty'].search([
                ('field_of_study_id', '=', self.filiere_id.id)
            ])
            # Remplir le champ des specialty_ids avec les IDs des specialty_ids trouvées
            self.specialty_ids = [(6, 0, specialty.ids)]
        else:
            # Si aucune école n'est sélectionnée, vider le champ des specialty_ids
            self.specialty_ids = [(5, 0, 0)]