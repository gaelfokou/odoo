import math

from odoo import models, fields, api
from odoo.exceptions import ValidationError




class Subject(models.Model):
    _name = 'siantou.ems.core.subject'
    _description = 'Cours'

    # Code du cours
    code = fields.Char(
        'Code',
        required=True
    )

    # Variable booléenne pour savoir si c'est un tronc commun ou pas
    shared_subject = fields.Boolean(
        'Tronc commun',
        default=True
    )

    # Nom du cours
    name = fields.Char(
        'Nom du cours',
        required=True
    )

    # Semestre auquel est lié le cours
    semester_id = fields.Many2one(
        'siantou.ems.core.year.semester',
        'Semestre',
        help='Semestre du cours',
        required=True,
        ondelete='restrict'
    )

    # Filière à laquelle appartient ce cours
    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        'Filière',
        help='Filière à laquelle appartient ce cours',
        required=True,
        ondelete='restrict'
    )

    # Niveau scolaire
    level_id = fields.Many2one(
        'siantou.ems.core.level',
        'Niveau',
        help='Niveau du cours',
        required=True,
        ondelete='restrict'
    )

    # Volume horaire du cours sur un semestre
    hours_credit = fields.Integer(
        'Volume horaire semestriel',
        help='Volume horaire du cours sur un semestre',
        default=0,
        required=True
    )

    # Volume horaire hebdommadaire sur un semestre
    weekly_hours_credit = fields.Integer(
        'Volume horaire hebdommadaire',
        compute='_compute_weekly_hours_credit',
        help='Volume horaire du cours sur une semaine',
        store=True
    )

    # Les enseignants qui dispensent ce cours
    teacher_ids = fields.Many2many(
        'hr.employee',
        relation='teacher_subject_rel',
        column1='subject_id',
        column2='employee_id',
        string='Professeurs',
        compute='_compute_teacher_ids',
        inverse='_set_teacher_ids'
    )
    
    # Les priorités pour chaque enseignant sur ce cours
    teacher_priority_ids = fields.One2many(
        'siantou.ems.core.teacher.subject.priority',
        'subject_id',
        'Priorités des enseignants'
    )

    # Contrainte SQL pour empêcher d'avoir le même code pour différentes filières
    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le cours doit être unique')
    ]

    # Contrainte logique pour s'assurer que le volume horaire est précisé et strictement supérieur à 0
    @api.constrains('hours_credit')
    def _check_hours_credit(self):
        for record in self:
            if record.hours_credit <= 0 :
                raise ValidationError("Le volume horaire semestriel doit être supérieur à 0")

    # Fonction pour le champ calculé weekly_hours_credit
    @api.depends('hours_credit', 'semester_id')
    def _compute_weekly_hours_credit(self):
        for record in self:
            if record.semester_id:
                # record.weekly_hours_credit = math.ceil(record.hours_credit / record.semester_id.number_of_week)

                # Toujours arrondir par la valeur supérieur d'un multiple de 2 afin d'avoir les cours de minimum 2h
                record.weekly_hours_credit = math.ceil(record.hours_credit / record.semester_id.number_of_week / 2) * 2
            else:
                record.weekly_hours_credit = 0

    # Méthode calculée pour teacher_ids afin de montrer les enseignants liés dans le modèle des priorités
    @api.depends('teacher_priority_ids')
    def _compute_teacher_ids(self):
        for record in self:
            record.teacher_ids = record.teacher_priority_ids.mapped('employee_id')

    # Méthode inverse pour ajouter/supprimer des enseignants dans le modèle des priorités avec une priorité par défaut de 1
    def _set_teacher_ids(self):
        for record in self:
            current_teacher_ids = record.teacher_priority_ids.mapped('employee_id').ids
            new_teacher_ids = record.teacher_ids.ids

            # Ajouter les nouveaux enseignants avec une priorité par défaut de 1
            to_add = set(new_teacher_ids) - set(current_teacher_ids)
            for teacher_id in to_add:
                self.env['siantou.ems.core.teacher.subject.priority'].create({
                    'employee_id': teacher_id,
                    'subject_id': record.id,
                    'priority': 1,
                })

            # Supprimer les enseignants enlevés de teacher_ids
            to_remove = set(current_teacher_ids) - set(new_teacher_ids)
            record.teacher_priority_ids.filtered(lambda p: p.employee_id.id in to_remove).unlink()