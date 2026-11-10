from odoo import models, fields, api, tools, _


class Level(models.Model):
    _name = 'siantou.ems.core.level'
    _description = 'Niveau'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    code = fields.Char(
        string='Code',
        required=True
    )

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

    def _default_year(self):
        year = self.env['siantou.ems.core.year'].sudo().search([
            ('active_user_ids', '=', self.env.user.id),
        ], limit=1)
        if not year:
            year = self.env['siantou.ems.core.year'].sudo().search([('is_active', '=', True)], limit=1)
        return year

    year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année académique',
        default=_default_year,
        required=True
    )

    _sql_constraints = [
        ('unique_code_year', 'unique(code,year_id)', 'Le code d\'un niveau ne peut être lié à une même année académique qu\'une seule fois.')
    ]
