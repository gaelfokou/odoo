from collections import defaultdict

from odoo import models, fields


class FieldOfStudy(models.Model):
    _name = 'siantou.ems.core.field_of_study' #== cursus'
    _description = 'Filières'

    # Code du programme
    code = fields.Char(
        'Code',
        required=True
    )

    # Nom du programme
    name = fields.Char(
        'Nom de la filière',
        required=True
    )
    cursus_id = fields.Many2one(
        'oe.school.course', 
        string='Cursus ou Cycle') #== cursus

    # Ensemble des cours de la filière
    subject_ids = fields.One2many(
        'siantou.ems.core.subject',
        'field_of_study_id',
        'Cours'
    )



    # Contrainte SQL pour empêcher d'avoir le même code pour différentes filières
    _sql_constraints = [
        ('unique_code', 'unique(code)', 'La filière doit être unique')
    ]

    def get_subject_ids_by_level(self):
        # Dictionnaire pour stocker les IDs des cours par niveau
        subject_ids_by_level = defaultdict(list)

        # Parcourt tous les niveaux de la filière
        for level in self.env['siantou.ems.core.level'].search([]):
            # Filtre les cours de cette filière et de ce niveau
            subjects = self.subject_ids.filtered(lambda s: s.level_id == level)
            if subjects:
                # Ajoute les IDs des cours au dictionnaire avec l'ID du niveau comme clé
                subject_ids_by_level[level.id] = subjects.mapped('id')

        return subject_ids_by_level
