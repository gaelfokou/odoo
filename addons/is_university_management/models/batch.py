from odoo import models, fields, api


class StudentBatch(models.Model):
    _name = 'is.university.school.student.batch'
    _description = 'Lots d\'étudiants'

    name = fields.Char(
        string="Nom du lot",
        help="Nom du lot, par exemple Lot A, Lot B"
    )

    school_id = fields.Many2one(
        'is.university.school',
        string="Ecole",
    )

    program_id = fields.Many2one(
        'is.university.school.program',
        string="Programme",
        help="Programme auquel ce lot est lié"
    )

    student_ids = fields.One2many(
        'is.university.school.student',
        'batch_id',
        string="Étudiants"
    )

    max_students = fields.Integer(
        string="Nombre max d\'étudiants par lot",
        related='school_id.max_students_per_batch',
        store=True,
    )

    current_size = fields.Integer(
        string="Nombre actuel d'étudiants",
        compute='_compute_current_size',
        store=True
    )

    @api.depends('student_ids')
    def _compute_current_size(self):
        for batch in self:
            batch.current_size = len(batch.student_ids)

    def create_new_batch(self, school_id, program_id):
        count_existing_batches = self.search_count([('program_id', '=', program_id.id)])
        new_batch_name = f"Lot {chr(65 + count_existing_batches)}"
        return self.create({
            'name': new_batch_name,
            'school_id': school_id.id,
            'program_id': program_id.id
        })

    @api.model
    def assign_batch(self, school_id, program_id):
        batches = self.search([
            ('program_id', '=', program_id.id),
            ('current_size', '<', school_id.max_students_per_batch)
        ], limit=1)

        if batches:
            return batches[0]
        else:
            return self.create_new_batch(school_id, program_id)
