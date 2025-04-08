from odoo import models, fields


class UniversityTeacher(models.Model):
    _name = 'is.university.teacher'
    _description = 'Enseignants'

    name = fields.Char(
        string="Nom",
        required=True
    )

    subject_ids = fields.Many2many(
        'is.university.subject',
        string='Cours du cursus',
        help="Les cours que cet enseignant donne"
    )

    availability_ids = fields.One2many(
        'is.university.teacher.availability',
        'teacher_id',
        string='Disponibilités'
    )
