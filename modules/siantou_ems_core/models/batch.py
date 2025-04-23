from odoo import models, fields, api, tools, _

class StudentBatch(models.Model):
    _name = 'siantou.ems.core.student.batch'
    _description = 'Lots d\'étudiants'

    name = fields.Char(
        string='Nom'
    )

    school_id = fields.Many2one(
        'siantou.ems.core.school',
        string='Ecole',
        required=True
    )

    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        string='Filière',
        required=True
    )

    specialty_id = fields.Many2one(
        'siantou.ems.core.specialty',
        string='Spécialité',
        required=True
    )

    option_id = fields.Many2one(
        'siantou.ems.core.option',
        string='Option',
    )

    level_id = fields.Many2one(
        'siantou.ems.core.level',
        string='Niveau',
        required=True
    )

    student_ids = fields.One2many(
        'oe.school.student',
        'batch_id',
        string='Étudiants du lot'
    )

    current_size = fields.Integer(
        string="Capacité actuelle",
        compute='_compute_current_size',
        store=True
    )

    @api.depends('student_ids')
    def _compute_current_size(self):
        for record in self:
            record.current_size = len(record.student_ids)

    def create_new_batch(self, school_id, field_of_study_id, specialty_id, option_id, level_id):
        count_existing_batches = self.search_count([
            ('school_id', '=', school_id),
            ('field_of_study_id', '=', field_of_study_id),
            ('specialty_id', '=', specialty_id),
            ('option_id', '=', option_id),
            ('level_id', '=', level_id),
        ])
        new_batch_name = f"Lot {chr(65 + count_existing_batches)}"
        return self.create({
            'name': new_batch_name,
            'school_id': school_id,
            'field_of_study_id': field_of_study_id,
            'specialty_id': specialty_id,
            'option_id': option_id,
            'level_id': level_id
        })

    @api.model
    def assign_batch(self, school_id, field_of_study_id, specialty_id, option_id, level_id):

        max_students_per_batch = self.env['siantou.ems.core.school'].browse(school_id).max_students_per_batch
        batch = self.search([
            ('school_id', '=', school_id),
            ('field_of_study_id', '=', field_of_study_id),
            ('specialty_id', '=', specialty_id),
            ('option_id', '=', option_id),
            ('level_id', '=', level_id),
            ('current_size', '<', max_students_per_batch)
        ], limit=1)

        if batch:
            return batch
        else:
            return self.create_new_batch(school_id, field_of_study_id, specialty_id, option_id, level_id)