from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import unique


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Variable booléenne pour identifier un enseignant
    is_teacher = fields.Boolean(
        'Est un enseignant'
    )

    # Variable booléenne pour identifier un employé permanent
    is_permanent = fields.Boolean(
        'Est un employé permanent'
    )

    # Matricule de l'enseignant
    identifier = fields.Char(
        'Matricule',
        required=True
    )

    # Les cours que dispense cet enseignant
    subject_ids = fields.Many2many(
        'siantou.ems.core.subject',
        relation='teacher_subject_rel',
        column1='employee_id',
        column2='subject_id',
        string='Cours dispensés'
    )

    # Les priorités aux cours dispensés
    subject_priority_ids = fields.One2many(
        'siantou.ems.core.teacher.subject.priority',
        'employee_id',
        'Cours dispensés avec les priorités'
    )

    # Quota horaire de cours pour un professeur permanent
    weekly_hours_limit = fields.Integer(
        'Quota horaire hebdommadaire',
        required=True
    )

    # Disponibilité de l'enseignant
    teacher_availability_ids = fields.One2many(
        'siantou.ems.core.teacher.availability',
        'employee_id',
        'Disponibilité'
    )


class TeacherAvailability(models.Model):
    _name = 'siantou.ems.core.teacher.availability'
    _description = 'Disponibilité des professeurs'

    # Enseignant lié
    employee_id = fields.Many2one(
        'hr.employee',
        'Enseignant',
        required=True,
        ondelete='cascade'
    )

    # Jour de la semaine
    day_of_week = fields.Selection([
        ('0', 'Lundi'),
        ('1', 'Mardi'),
        ('2', 'Mercredi'),
        ('3', 'Jeudi'),
        ('4', 'Vendredi'),
        ('5', 'Samedi'),
    ],
        'Jour de la semaine',
        required=True
    )

    # Heure de début de disponibilité
    start_time = fields.Float(
        'Heure de début',
        required=True,
        widget='time'
    )

    # Heure de fin de disponibilité
    end_time = fields.Float(
        'Heure de fin',
        required=True,
        widget='time'
    )

    @api.constrains('start_time', 'end_time')
    def _check_time(self):
        for record in self:
            if record.start_time >= record.end_time:
                raise ValidationError("L'heure de fin doit être supérieure à l'heure de début")


class TeacherSubjectPriority(models.Model):
    _name = 'siantou.ems.core.teacher.subject.priority'
    _description = 'Priorité du professeur au cours'

    # Professeur pour lequel on souhaite définir la priorité sur le cours
    employee_id = fields.Many2one(
        'hr.employee',
        'Enseignant',
        required=True,
        ondelete='cascade'
    )

    # Cours pour lequel on souhaite définir la priorité de l'enseignant
    subject_id = fields.Many2one(
        'siantou.ems.core.subject',
        'Cours',
        required=True,
        ondelete='cascade'
    )

    # Priorité de l'enseignant pour ce cours
    priority = fields.Integer(
        'Priorité',
        help='Le professeur avec le nombre le plus élevé est prioritaire (va de 1 à 10)',
        required=True
    )

    # Contrainte SQL pour s'assurer de l'unicité du couple (professeur, couple) dans la base de donnée
    _sql_constraints = [
        ('unique_teacher_subject_rel', 'unique(employee_id, subject_id)', 'Un enseignant ne peut être lié à un même cours qu\'une seule fois.')
    ]

    # Contrainte logique pour s'assurer que l'utilisateur donne une priorité entre 1 et 10
    @api.constrains('priority')
    def _check_priority(self):
        for record in self:
            if record.priority < 1 or record.priority > 10:
                raise ValidationError("La priorité va de 1 à 10")

    # Fonction pour obtenir la liste des enseignants par priorité décroissante
    def get_teachers_by_priority(self, subject_id):
        return self.env['siantou.ems.core.teacher.subject.priority'].search(
            [('subject_id', '=', subject_id)],
            order='priority DESC'
        )