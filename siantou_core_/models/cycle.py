from odoo import _, api, fields, models, tools
"""
Gérer vos cycles ici
par exemple : bts, hnd, etc...
"""

class SiantouCycle(models.Model):
    _name = 'siantou.cycle'
    _description = 'Gérer les cycles des étudiants'

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Nom", required=True)
    filiere_ids = fields.One2many(
        'siantou.filiere', 
        'cycle_id',
        string='Liste des filières',
    )


    _sql_constraints = [
        ('unique_code', 'UNIQUE (code)','Ce code existe déjà'),
        ('unique_name', 'UNIQUE (name)','Ce Nom existe déjà'),
    ]

    def get_filieres(self):
        filieres = self.env['siantou.filiere'].search([('cycle_id', 'in', self.ids)])
        return filieres

