from odoo import models, fields, api, tools, _

class StudentBatch(models.Model):
    _name = 'siantou.ems.core.student.batch'
    _description = 'Lots d\'étudiants'

    name = fields.Char(
        string='Nom'
    )

    school_id = fields.Many2one(
        'siantou.ems.core.school',
        string='École',
    )

    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        string='Filière',
    )

    specialty_id = fields.Many2one(
        'siantou.ems.core.specialty',
        string='Spécialité',
    )

    option_id = fields.Many2one(
        'siantou.ems.core.option',
        string='Option',
    )

    level_id = fields.Many2one(
        'siantou.ems.core.level',
        string='Niveau',
    )

    class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe',
        required=True,
    )

    student_ids = fields.Many2many(
        'oe.school.student',
        'batch_student_rel',
        'batch_id',
        'student_id',
        string='Liste des étudiants',
        compute='_compute_students',
        store=False
    )

    @api.depends('class_id')
    def _compute_students(self):
        for record in self:
            record.student_ids = record.class_id.student_ids

    current_size = fields.Integer(
        string="Capacité actuelle",
        compute='_compute_current_size',
        store=True
    )

    @api.depends('class_id')
    def _compute_current_size(self):
        for record in self:
            record.current_size = len(record.class_id.student_ids.ids)

    def create_new_batch(self, class_id):
        count_existing_batches = self.search_count([
            ('class_id', '=', class_id),
        ])
        new_batch_name = f"Lot {chr(65 + count_existing_batches)}"
        return self.create({
            'name': new_batch_name,
            'class_id': class_id,
        })

    @api.model
    def assign_batch(self, class_id):
        max_students_per_batch = self.env['siantou.ems.core.class'].browse(class_id).school_id.max_students_per_batch
        batch = self.env['siantou.ems.core.student.batch'].search([
            ('class_id', '=', class_id),
            ('current_size', '<', max_students_per_batch)
        ], limit=1)

        if batch:
            return batch
        else:
            return self.create_new_batch(class_id)