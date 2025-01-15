from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import psycopg2
from odoo.tools import unique
import logging

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _name = 'hr.employee'
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
        string='Cours dispensés',
        compute='_compute_subject_ids',
        inverse='_set_subject_ids'
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

    # Relation avec les emplois du temps
    timetable_ids = fields.One2many(
        'siantou.ems.timetable.timetable',  # Nom du modèle cible
        'employee_id',                     # Champ de relation dans le modèle Timetable
        string='Emplois du temps',
        help="Liste des emplois du temps associés à l'enseignant."
    )

    def create_employee_user(self, employee_id):
        try:
            user_ids = self.env['res.users'].search([
                ('employee_id', '=', employee_id.id),
            ])
            user_ids = list(user_ids)
            if len(user_ids) == 0:
                name = employee_id.name
                # email = employee_id.work_email
                username = name.replace(' ', '.').lower()
                email = username + '@siantou.net'
                password = username
                i = 0
                while True:
                    user_ids = self.env['res.users'].search([
                        ('login', '=', email),
                    ])
                    user_ids = list(user_ids)
                    if len(user_ids) > 0:
                        i = i + 1
                        email = username + f'.{i}' + '@siantou.net'
                        password = username + f'.{i}'
                    else:
                        break
                if employee_id.is_teacher:
                    group_id = self.env.ref('base.group_portal')
                    user_id = self.env['res.users'].create({
                        'login': email,
                        'name': name,
                        'password' : password,
                        'groups_id': [(6, 0, [group_id.id])],
                    })
                else:
                    user_id = self.env['res.users'].create({
                        'login': email,
                        'name': name,
                        'password' : password,
                    })
                employee_id.write({
                    'work_email': email,
                    'user_id': user_id.id,
                })
        except psycopg2.errors.NotNullViolation as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
            raise ValidationError("L'adresse e-mail professionnelle n'est pas renseignée.")
        except psycopg2.Error as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except Exception as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

    @api.model
    def create(self, vals):
        employee_id = super(HrEmployee, self).create(vals)

        self.create_employee_user(employee_id)

        return employee_id

    def action_create_employee_user(self):
        employee_ids = self.env['hr.employee'].search([
            ('id', '=', self.id),
        ])
        employee_ids = list(employee_ids)
        if len(employee_ids) > 0:
            employee_id = employee_ids[0]
            self.create_employee_user(employee_id)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_create_all_employee_user(self):
        employee_ids = self.env['hr.employee'].search([])
        for employee_id in employee_ids:
            self.create_employee_user(employee_id)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.depends('subject_priority_ids')
    def _compute_subject_ids(self):
        """ Méthode de calcul pour subject_ids pour afficher les cours à partir des enregistrements de priorité. """
        for record in self:
            record.subject_ids = record.subject_priority_ids.mapped('subject_id')

    def _set_subject_ids(self):
        """ Méthode inverse pour ajouter/met à jour les cours dans le modèle des priorités avec une priorité de 1. """
        for record in self:
            # Identifie les cours actuels associés aux priorités
            current_subject_ids = record.subject_priority_ids.mapped('subject_id').ids
            # Identifie les nouveaux cours ajoutés dans subject_ids
            new_subject_ids = record.subject_ids.ids

            # Ajouter les nouveaux cours avec priorité 1
            to_add = set(new_subject_ids) - set(current_subject_ids)
            for subject_id in to_add:
                self.env['siantou.ems.core.teacher.subject.priority'].create({
                    'employee_id': record.id,
                    'subject_id': subject_id,
                    'priority': 1,
                })

            # Supprimer les cours retirés de subject_ids
            to_remove = set(current_subject_ids) - set(new_subject_ids)
            record.subject_priority_ids.filtered(lambda p: p.subject_id.id in to_remove).unlink()


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