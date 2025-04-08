from odoo import models, fields


class UniversitySemester(models.Model):
    _name = 'is.university.semester'
    _description = 'Semestres universitaires'

    name = fields.Char(
        string="Nom",
        required=True,
        help="Nom du semestre, par exemple Semestre 1, Semestre 2"
    )

    academic_year_id = fields.Many2one(
        'is.university.academic_year',
        string="Année académique",
        required=True
    )

    start_date = fields.Date(
        string="Date de début",
        required=True
    )

    end_date = fields.Date(
        string="Date de fin",
        required=True
    )
