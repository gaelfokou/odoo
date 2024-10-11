from odoo import _, api, fields, models, tools
"""
Gérer vos options ici
"""

class SiantouOption(models.Model):
    _name = 'siantou.option'
    _description = 'Gérer les options des étudiants'

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Nom", required=True)
    specialite_id = fields.Many2one(
        'siantou.specialite',
        string='Filière',
    )

