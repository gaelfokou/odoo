from odoo import models, fields


class UniversitySchool(models.Model):
    _name = 'is.university.school'
    _description = 'Ecoles'

    name = fields.Char(
        string="Nom",
        help="Nom de l\'école",
        required=True
    )

    field_of_study_ids = fields.One2many(
        'is.university.school.field_of_study',
        'school_id',
        'Filières'
    )

    max_students_per_batch = fields.Integer(
        string='Nombre max d\'étudiants par lot',
        required=True,
        default=60
    )
