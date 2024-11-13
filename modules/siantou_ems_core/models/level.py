from odoo import models, fields


class Level(models.Model):
    _name = 'siantou.ems.core.level'
    _description = 'Niveaux'

    # Nom du niveau
    name = fields.Char(
        'Nom du niveau',
        required=True,
    )

    # Description du niveau
    description = fields.Text(
        'Description',
    )

    # Ensemble des cours du niveau
    subject_ids = fields.One2many(
        'siantou.ems.core.subject',
        'level_id',
        'Cours'
    )

    batch_ids = fields.One2many(
        'siantou.ems.core.student.batch',
        'level_id',
        string='Lots du niveau'
    )
    
    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Nom déjà utilisé'),
    ]