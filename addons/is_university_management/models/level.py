from odoo import models, fields


class SchoolLevel(models.Model):
    _name = 'is.university.school.level'
    _description = 'Niveau d\'étude'

    name = fields.Char(
        string="Nom",
        help="Le nom du niveau d'étude par exemple BAC + 1",
        required=True
    )

    level = fields.Integer(
        string='Niveau',
        required=True
    )
