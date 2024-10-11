from odoo import _, api, fields, models, tools
"""
Gérer vos specialitées ici
par exemple : génie logiciel, batiments, etc...
"""

class SiantouNiveau(models.Model):
    _name = 'siantou.niveau'
    _description = 'Gérer les niveaux des étudiants'

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Nom", required=True)

    filiere_ids = fields.Many2many(
        'siantou.filiere',
        string='Liste des filières',
    )

