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
        ('unique_code', 'unique(code)', 'Le code doit être unique'),
        ('unique_name', 'unique(name)', 'Le nom doit être unique'),
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

    # Ensemble des cours de la filière
    # subject_ids = fields.One2many(
    #     'siantou.ems.core.subject',
    #     'field_of_study_id',
    #     'Cours'
    # )
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

    student_ids = fields.One2many(
        'oe.school.student',
        'field_of_study_id',
        string='Liste des étudiants'
    )

    # Contrainte SQL pour empêcher d'avoir le même code pour différentes filières
    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code doit être unique'),
        ('unique_name', 'unique(name)', 'Le nom doit être unique'),
    ]

    # def get_subject_ids_by_level(self):
    #     # Dictionnaire pour stocker les IDs des cours par niveau
    #     subject_ids_by_level = defaultdict(list)

    #     # Parcourt tous les niveaux de la filière
    #     for level in self.env['siantou.ems.core.level'].search([]):
    #         # Filtre les cours de cette filière et de ce niveau
    #         subjects = self.subject_ids.filtered(lambda s: s.level_id == level)
    #         if subjects:
    #             # Ajoute les IDs des cours au dictionnaire avec l'ID du niveau comme clé
    #             subject_ids_by_level[level.id] = subjects.mapped('id')

    #     return subject_ids_by_level
