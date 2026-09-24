from odoo import models, fields, api, tools, _


class Level(models.Model):
    _name = 'siantou.ems.core.level'
    _description = 'Niveau'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    name = fields.Char(
        string='Nom',
        required=True,
    )

    description = fields.Text(
        string='Description',
    )

    cycle_ids = fields.Many2many('oe.school.course', 'course_level_rel', 'level_id', 'cycle_id', string='Cursus ou Cycles')

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

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code du niveau doit être unique.'),
    ]
