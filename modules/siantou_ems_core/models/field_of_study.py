from collections import defaultdict

from odoo import models, fields




class SpecialtyOfStudy(models.Model):
    _name = 'siantou.ems.core.specialty' #== cursus'
    _description = 'Gestion des spécialités'

    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        string='Filière ',
        required=True,
    )

    # Code du programme
    code = fields.Char(
        'Code',
        required=True
    )

    # Nom du programme
    name = fields.Char(
        'Nom de la spécialité',
        required=True
    )

    # Contrainte SQL pour empêcher d'avoir le même code pour différentes filières
    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code de la spécialité doit être unique.'),
    ]




class FieldOfStudy(models.Model):
    _name = 'siantou.ems.core.field_of_study' #== cursus'
    _description = 'Gestion des Filières'

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

    school_id = fields.Many2one(
        'siantou.ems.core.school',
        string='Ecole',
    )

    cursus_id = fields.Many2one(
        'oe.school.course', 
        string='Cursus ou Cycle') #== cursus

    # Ensemble des spécialités de la filière
    specialty_ids = fields.One2many(
        'siantou.ems.core.specialty',
        'field_of_study_id',
        'Liste des spécialités'
    )

    batch_ids = fields.One2many(
        'siantou.ems.core.student.batch',
        'field_of_study_id',
        string='Lots de la filière'
    )

    # Ajouter un champ de relation vers hr.department pour lier la filière au département
    department_id = fields.Many2one(
        'hr.department',
        string='Département'
    )

    slot_id = fields.Many2one(
        'siantou.ems.timetable.slot',
        string='Créneau horaire',
    )

    # Contrainte SQL pour empêcher d'avoir le même code pour différentes filières
    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code de la filière doit être unique.'),
    ]

    def get_subject_ids_by_level(self):
        # Dictionnaire pour stocker les IDs des cours par niveau
        subject_ids_by_level = {}

        # Parcourt tous les niveaux de la filière
        levels = self.env['siantou.ems.core.level'].search([])
        levels = list(levels)
        for level in levels:
            subject_ids_by_level[level.id] = []
            # Filtre les cours de cette filière et de ce niveau
            classes = self.env['siantou.ems.core.class'].search([
                ('niveau_id', '=', level.id),
                ('filiere_id', '=', self.id)
            ])
            classes = list(classes)
            for classe in classes:
                subjects = self.env['siantou.ems.core.subject'].search([
                    ('ue_ids', 'in', classe.ue_ids.ids),
                ])
                subjects = list(subjects)
                for subject in subjects:
                    if not subject.id in subject_ids_by_level[level.id]:
                        subject_ids_by_level[level.id].append(subject.id)
            if len(subject_ids_by_level[level.id]) == 0:
                del(subject_ids_by_level[level.id])

        return subject_ids_by_level
