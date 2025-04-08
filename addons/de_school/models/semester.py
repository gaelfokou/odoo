from odoo import models, fields, api
from odoo.exceptions import ValidationError


class UniversitySemester(models.Model):
    _name = 'oe.school.year.semester'
    _description = 'Semestres universitaires'

    name = fields.Char(
        string="Nom",
        required=True,
        help="Nom du semestre, par exemple Semestre 1, Semestre 2"
    )

    academic_year_id = fields.Many2one(
        'oe.school.year',
        string="Année académique",
        required=True
    )

    date_start = fields.Date(
        string="Date de début",
        required=True
    )

    date_end = fields.Date(
        string="Date de fin",
        required=True
    )

    subject_id = fields.Many2many(
        'oe.school.subject',
        relation='',

    )

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Le semestre doit être unique')
    ]

    @api.constrains('date_start', 'date_end')
    def _check_date_overlap(self):
        for semester in self:
            # Check for overlapping dates in other academic years
            overlapping_semester = self.search([
                ('id', '!=', semester.id),
                ('date_start', '<=', semester.date_end),
                ('date_end', '>=', semester.date_start),
            ])
            if overlapping_semester:
                raise ValidationError("Les semestres ne peuvent se supperposer.")
