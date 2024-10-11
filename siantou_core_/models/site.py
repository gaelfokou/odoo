from odoo import _, api, fields, models, tools
"""
Gérer vos site ou campus ici
"""

class SiantouSite(models.Model):

    _name = 'siantou.site'
    _description = 'Gérer les sites'

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Nom", required=True)
    batiment_ids = fields.One2many(
        comodel_name='siantou.batiment',
        inverse_name='site_id',
        string='Batîments'
    )


