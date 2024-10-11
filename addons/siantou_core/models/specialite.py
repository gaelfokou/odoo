from odoo import _, api, fields, models, tools
"""
Gérer vos filières ici
"""

class SiantouSpecialite(models.Model):
    _name = 'siantou.specialite'
    _description = 'Gérer les spécialités'

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Nom", required=True)
    filiere_id = fields.Many2one(
        'siantou.filiere',
        string='Filière', 
        required=True
    )
    option_ids = fields.One2many(
        comodel_name='siantou.option',
        inverse_name='specialite_id',
        string='Liste des options',
    )