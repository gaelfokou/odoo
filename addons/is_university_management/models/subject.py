from odoo import models, fields


class UniversitySubject(models.Model):
    _name = 'is.university.subject'
    _description = 'Cours'

    name = fields.Char(
        string="Nom",
        required=True
    )

    teacher_ids = fields.Many2many(
        'is.university.teacher',
        string="Enseignants",
        help="Les professeurs qui donnent ce cours",
    )

    program_id = fields.Many2one(
        'is.university.school.program',
        string="Programme"
    )

    semester_id = fields.Many2one(
        'is.university.semester',
        string="Semestre",
        help="Le semestre durant lequel ce cours est donné"
    )

    duration = fields.Float(
        string="Durée (heures)",
        help="Durée totale du cours"
    )
