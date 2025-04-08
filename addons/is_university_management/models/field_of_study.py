from odoo import models, fields


class SchoolFieldofStudy(models.Model):
    _name = 'is.university.school.field_of_study'
    _description = 'Filières'

    name = fields.Char(
        string="Nom",
        help="Nom de la filière",
        required=True
    )

    school_id = fields.Many2one(
        'is.university.school',
        string="Ecole",
        help="Ecole liée à la filière",
        required=True
    )
