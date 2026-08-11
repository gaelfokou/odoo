from odoo import models, fields, api, tools, _

class UniversityPartner(models.Model):
    _name = 'siantou.university.partner'
    _description = 'Universitées partenaires'

    #===== Nom
    name = fields.Char(
        string='Nom',
        required=True,
    )

    image = fields.Image(string='Image')
    field_of_study_ids = fields.Many2many(
        'siantou.ems.core.field_of_study',
        string='Spécialités',
        required=True,
    )

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Ce nom existe déjà'),
    ]

