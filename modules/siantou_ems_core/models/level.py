from odoo import models, fields

class Level(models.Model):
    _name = 'siantou.ems.core.level'
    _description = 'Niveaux'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    # Nom du niveau
    name = fields.Char(
        'Nom du niveau',
        required=True,
    )

    # Description du niveau
    description = fields.Text(
        'Description',
    )

    cycle_ids = fields.Many2many('oe.school.course', 'course_level_rel', 'level_id', 'cycle_id', string='Cursus ou Cycles')

    # Ensemble des cours du niveau
    class_ids = fields.One2many(
        'siantou.ems.core.class',
        'level_id',
        string='Classes'
    )

    batch_ids = fields.One2many(
        'siantou.ems.core.student.batch',
        'level_id',
        string='Lots du niveau'
    )

    semester_ids = fields.Many2many(
        'siantou.ems.core.year.semester',
        'semester_level_rel',
        'level_id',
        'semester_id',
        string='Semestres',
    )

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Le nom du niveau doit être unique.'),
    ]