from odoo import _, api, fields, models, tools
"""
Gérer vos salles de cours ici
"""

class SiantouSalle(models.Model):
    _name = 'siantou.salle'
    _description = 'Gérer les salles de cours'

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Nom", required=True)
    batiment_id = fields.Many2one(
        'siantou.batiment',
        string='Site',
    )







