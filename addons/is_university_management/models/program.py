from odoo import models, fields, api


class SchoolProgram(models.Model):
    _name = 'is.university.school.program'
    _description = 'Programme'

    name = fields.Char(
        string="Cursus",
        required=True
    )

    field_of_study_id = fields.Many2one(
        'is.university.school.field_of_study',
        string="Filière",
        help="Filière",
        required=True
    )

    level_id = fields.Selection(
        selection=lambda self: self._get_level_selection(),
        string='Niveau'
    )

    subject_ids = fields.One2many(
        'is.university.subject',
        'program_id',
        string="Cours du cursus"
    )

    student_ids = fields.One2many(
        'is.university.school.student',
        'program_id',
        string="Etudiants du cursus"
    )

    @api.model
    def _get_level_selection(self):
        levels = self.env['is.university.school.level'].search([])
        if not levels:
            return []
        return [(level.id, level.name) for level in levels]
