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
    specialite_ids = fields.One2many(
        'siantou.specialite',
        'filiere_id',
        string='Liste des spécialités',
    )

