from odoo import _, api, fields, models, tools
"""
Gérer vos matières ici
"""

class SiantouMatiere(models.Model):

    _name = 'siantou.matiere'
    _description = 'Gérer les matieres des étudiants'

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Nom", required=True)
    nbre_cm = fields.Integer(string="Nombre de cours", required=True)
    nbre_tp = fields.Integer(string="Nombre de travaux pratique", required=True)
    nbre_tpe = fields.Integer(string="Nombre de travaux pratique ", required=True)
    nbre_credit = fields.Integer(string="Nombre de crédit ", required=True)
    description = fields.Html(string="Notes ")
    specialite_id = fields.Many2one(
        'siantou.specialite',
        string='Spécialité', 
        required=True
    )
    option_id = fields.Many2one(
        'siantou.option',
        string='Option',
    )


