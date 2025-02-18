from odoo import models, fields


class Level(models.Model):
    _name = 'siantou.ems.core.level'
    _description = 'Gestion des niveaux'

    # Nom du niveau
    name = fields.Char(
        'Nom du niveau',
        required=True,
    )

    # Description du niveau
    description = fields.Text(
        'Description',
    )

    cycle_ids = fields.Many2many('oe.school.course', string="Cycles")

    # Ensemble des cours du niveau
    class_ids = fields.One2many(
        'siantou.ems.core.class',
        'niveau_id',
        'Cours'
    )

    batch_ids = fields.One2many(
        'siantou.ems.core.student.batch',
        'level_id',
        string='Lots du niveau'
    )
    
    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Le nom du niveau doit être unique.'),
    ]