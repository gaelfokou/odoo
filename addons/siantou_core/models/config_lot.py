from odoo import _, api, fields, models, tools
"""
Gérer vos configurations des lots ici
"""

class SiantouMatiere(models.Model):
    _name = 'siantou.config_lot'
    _description = 'Gérer les lots des étudiants'

    name = fields.Char(string="Nom", required=True)
    nbre_place = fields.Integer("Nombre de place", required=True)







