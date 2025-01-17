from odoo import models, fields


class UniversityPartner(models.Model):
    _name = 'siantou.university.partner'
    _description = 'Gestion des universitées partenaires'


    #===== Nom
    name = fields.Char(
        'Nom',
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

