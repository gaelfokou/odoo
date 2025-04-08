from odoo import models, fields, api


class SchoolStudent(models.Model):
    _name = 'is.university.school.student'
    _description = 'Etudiants'

    name = fields.Char(
        string="Nom",
        required=True
    )

    school_id = fields.Many2one(
        'is.university.school',
        string="Ecole",
        required=True
    )

    program_id = fields.Many2one(
        'is.university.school.program',
        string="Programme",
        required=True
    )

    batch_id = fields.Many2one(
        'is.university.school.student.batch',
        string="Lot d'étudiants",
        help="Lot auquel l'étudiant appartient"
    )

    @api.model
    def create(self, vals):
        program = self.env['is.university.school.program'].browse(vals.get('program_id'))

        batch = self.env['is.university.school.student.batch'].assign_batch(self.school_id, self.program_id)

        vals['batch_id'] = batch.id
        return super(SchoolStudent, self).create(vals)
