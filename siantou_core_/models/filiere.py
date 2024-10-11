from odoo import _, api, fields, models, tools
"""
Gérer vos specialitées ici
par exemple : génie logiciel, batiments, etc...
"""

class SiantouFiliere(models.Model):
    _name = 'siantou.filiere'
    _description = 'Gérer les filières des étudiants'

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Nom", required=True)
    cycle_id = fields.Many2one(
        'siantou.cycle',
        string='Cycle',
        required=True
    )
    specialite_ids = fields.One2many(
        'siantou.specialite',
        'filiere_id',
        string='Liste des spécialités',
    )
    niveau_ids = fields.Many2many('siantou.niveau', string="Niveaux académiques")

