from odoo import _, api, fields, models, tools
"""
Gérer vos batiments ici
"""

class SiantouBatiment(models.Model):
    _name = 'siantou.batiment'
    _description = 'Gérer les batiments'

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Nom", required=True)
    site_id = fields.Many2one(
        'siantou.site',
        string='Site(Campus)',
        required=True
    )


