from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
import psycopg2
from odoo.tools import unique
import re
import logging

_logger = logging.getLogger(__name__)

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    name = fields.Char(string="Nom(s) et prénom(s)", compute='_compute_name', store=True)
    last_name = fields.Char(string="Nom(s)", required=True)
    first_name = fields.Char(string="Prénom(s)")

    # Variable booléenne pour identifier un enseignant
    is_teacher = fields.Boolean(
        'Est un enseignant',
        default=True,
    )

    # Variable booléenne pour identifier un employé permanent
    is_permanent = fields.Boolean(
        'Est un permanent',
        default=False,
    )

    # Matricule de l'enseignant
    identifier = fields.Char(
        'Matricule',
        # required=True
    )

    # Les cours que dispense cet enseignant
    subject_ids = fields.Many2many(
        'siantou.ems.core.subject',
        'teacher_subject_rel',
        'employee_id',
        'subject_id',
        string='Cours dispensés',
        # compute='_compute_subject_ids',
        # inverse='_set_subject_ids'
    )

    # Les priorités de chaque cours sur cet enseignant
    subject_priority_ids = fields.One2many(
        'siantou.ems.core.teacher.subject.priority',
        'employee_id',
        'Priorités des cours'
    )

    # Quota horaire hebdommadaire de cours pour un enseignant permanent
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

    birthday = fields.Date(
        'Date de naissance',
    )

    @api.depends('last_name', 'first_name')
    def _compute_name(self):
        for record in self:
            last_name = record.last_name if record.last_name else ''
            first_name = record.first_name if record.first_name else ''
            name = '{} {}'.format(last_name, first_name)
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            record.name = name

    @api.onchange('last_name', 'first_name')
    def _onchange_name(self):
        for record in self:
            last_name = record.last_name if record.last_name else ''
            first_name = record.first_name if record.first_name else ''
            name = '{} {}'.format(last_name, first_name)
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            record.name = name

    # Contrainte logique pour s'assurer que le quota horaire hebdommadaire de cours pour un enseignant permanent est de 24
    @api.constrains('weekly_hours_limit')
    def _check_weekly_hours_limit_permanent(self):
        for record in self:
            if record.is_permanent and record.weekly_hours_limit != 24:
                raise ValidationError("Vous devez définir le quota horaire hebdommadaire de cours pour un enseignant permanent à 24")

    def create_employee_user(self, employee):
        try:
            ecole = 'IUS'
            ecole = ecole[:4]
            ecole = ecole.upper()
            if not employee.identifier or not employee.identifier.strip():
                identifier = ecole + self.env['ir.sequence'].next_by_code('hr.employee')
                while True:
                    employee_id = self.env['hr.employee'].search([
                        ('id', '!=', employee.id),
                        ('identifier', '=', identifier),
                    ], limit=1)
                    if employee_id:
                        identifier = ecole + self.env['ir.sequence'].next_by_code('hr.employee')
                    else:
                        break
            else:
                identifier = employee.identifier
                while True:
                    if identifier.find('2024') != -1:
                        identifier = identifier.replace('2024', '')
                    else:
                        break
                identifier = '{}2024'.format(identifier)
            password = identifier
            if employee.work_email and employee.work_email.strip():
                email = employee.work_email
            else:
                last_name = employee.last_name if employee.last_name else ''
                while True:
                    if last_name.find('  ') != -1:
                        last_name = last_name.replace('  ', ' ')
                    else:
                        break
                last_name = last_name.strip()
                last_name = last_name.split(' ')
                first_name = employee.first_name if employee.first_name else ''
                while True:
                    if first_name.find('  ') != -1:
                        first_name = first_name.replace('  ', ' ')
                    else:
                        break
                first_name = first_name.strip()
                first_name = first_name.split(' ')
                if len(first_name) > 1:
                    name = '{} {} {}'.format(first_name[0], last_name[0], first_name[1])
                else:
                    name = '{} {}'.format(first_name[0], last_name[0])
                # name = employee.name
                while True:
                    if name.find('  ') != -1:
                        name = name.replace('  ', ' ')
                    else:
                        break
                name = name.strip()
                username = name.lower()
                username = username.split(' ')
                username = username[0:3]
                if len(username) == 1:
                    username = username[0]
                elif len(username) == 2:
                    username = '{}{}'.format(username[0][0:1], username[1])
                elif len(username) == 3:
                    username = '{}{}{}'.format(username[0][0:1], username[1], username[2][0:1])
                email = username + '@siantou.net'
                i = 0
                while True:
                    res_user_id = self.env['res.users'].search([
                        ('login', '=', email),
                    ], limit=1)
                    employee_id = self.env['hr.employee'].search([
                        ('id', '!=', employee.id),
                        ('work_email', '=', email),
                    ], limit=1)
                    if res_user_id or employee_id:
                        i = i + 1
                        email = username + f'{i}' + '@siantou.net'
                    else:
                        break
            employee.write({
                'identifier': identifier,
                'work_email': email,
            })
            user_id = self.env['res.users'].search([
                ('login', '=', email),
            ], limit=1)
            if user_id:
                user_id.unlink()
            if employee.is_teacher:
                group_id = self.env.ref('base.group_portal')
                user_id = self.env['res.users'].with_context(no_reset_password=True).create({
                    'login': email,
                    'name': employee.name,
                    'password' : password,
                    'groups_id': [(6, 0, [group_id.id])],
                })
            else:
                user_id = self.env['res.users'].with_context(no_reset_password=True).create({
                    'login': email,
                    'name': employee.name,
                    'password' : password,
                })
            # self.env.cr.commit()
        except psycopg2.errors.NotNullViolation as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except psycopg2.Error as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except Exception as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

    def update_subject_priority(self, employee):
        try:
            subject_ids = employee.subject_ids.ids
            exist_subject_ids = []
            for subject_priority_id in employee.subject_priority_ids:
                if subject_priority_id.subject_id.id not in subject_ids:
                    subject_priority_id.unlink()
                else:
                    exist_subject_ids.append(subject_priority_id.subject_id.id)
            for subject_id in employee.subject_ids:
                if subject_id.id not in exist_subject_ids:
                    employee.subject_priority_ids.create({
                        'employee_id': employee.id,
                        'subject_id': subject_id.id,
                    })
            # self.env.cr.commit()
        except psycopg2.errors.NotNullViolation as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except psycopg2.Error as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except Exception as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

    @api.model
    def create(self, vals):
        if vals['work_email'] and vals['work_email'].strip():
            employee_id = self.env['hr.employee'].search([('work_email', '=', vals['work_email'])], limit=1)
            if employee_id:
                return None

        employee = super(HrEmployee, self).create(vals)

        self.create_employee_user(employee)

        self.update_subject_priority(employee)

        return employee

    def write(self, vals):
        employee = self.env['hr.employee'].search([('id', '=', self.id)], limit=1)

        res = super(HrEmployee, self).write(vals)

        self.update_subject_priority(employee)

        return res

    def action_create_employee_user(self):
        employee = self.env['hr.employee'].search([
            ('id', '=', self.id),
        ], limit=1)
        if employee:
            self.create_employee_user(employee)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_create_all_employee_user(self):
        active_ids = self.env.context.get('active_ids', [])
        employee_ids = self.env['hr.employee'].browse(active_ids)
        for employee in employee_ids:
            self.create_employee_user(employee)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    # @api.depends('subject_priority_ids')
    # def _compute_subject_ids(self):
    #     """ Méthode de calcul pour subject_ids pour afficher les cours à partir des enregistrements de priorité. """
    #     for record in self:
    #         record.subject_ids = record.subject_priority_ids.mapped('subject_id')

    # def _set_subject_ids(self):
    #     """ Méthode inverse pour ajouter/met à jour les cours dans le modèle des priorités avec une priorité de 1. """
    #     for record in self:
    #         # Identifie les cours actuels associés aux priorités
    #         current_subject_ids = record.subject_priority_ids.mapped('subject_id').ids
    #         # Identifie les nouveaux cours ajoutés dans subject_ids
    #         new_subject_ids = record.subject_ids.ids

    #         # Ajouter les nouveaux cours avec priorité 1
    #         to_add = set(new_subject_ids) - set(current_subject_ids)
    #         for subject_id in to_add:
    #             self.env['siantou.ems.core.teacher.subject.priority'].create({
    #                 'employee_id': record.id,
    #                 'subject_id': subject_id,
    #                 'priority': 1,
    #             })

    #         # Supprimer les cours retirés de subject_ids
    #         to_remove = set(current_subject_ids) - set(new_subject_ids)
    #         record.subject_priority_ids.filtered(lambda p: p.subject_id.id in to_remove).unlink()

    def action_open_filter(self):
        view_id = self.env.ref('siantou_ems_core.teacher_filter_wizard').id
        return {
            'name': 'Filtre des enseignants',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teacher.filter.wizard',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
        }

    def action_reset_filter(self):
        self.env['ir.config_parameter'].set_param(f'filter.{self.env.user.id}', '')
        action = self.env.ref('siantou_ems_core.action_show_teacher').read()[0]
        action.update({
            'target': 'main',
        })
        return action

    def action_print_pdf(self):
        active_ids = self.env.context.get('active_ids', [])
        teachers = self.env['hr.employee'].browse(active_ids)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')
        report_data = self.env['teacher.print.wizard'].create({
            'is_teacher': True,
        })
        domain = [('id', 'in', active_ids)]
        data = report_data.print_teacher_report_data(domain)

        # Appeler le rapport PDF
        if not data['docdata']['teacher_data']:
            raise UserError('Aucune donnée trouvée')
        report_action = self.env.ref('siantou_ems_core.action_report_teacher')
        return report_action.report_action(self, data=data)

class TeacherAvailability(models.Model):
    _name = 'siantou.ems.core.teacher.availability'
    _description = 'Disponibilité des enseignants'

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
        ('6', 'Dimanche'),
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
    _description = 'Priorité du enseignant au cours'

    # Enseignant pour lequel on souhaite définir la priorité sur le cours
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
        help='Le enseignant avec le nombre le plus élevé est prioritaire (va de 1 à 10)',
        default=1,
        required=True
    )

    # Taux horaire du cours sur un enseignant
    hourly_rate = fields.Float(
        'Taux horaire',
        help='Taux horaire du cours sur un enseignant',
        default=0,
        required=True
    )

    # Contrainte SQL pour s'assurer de l'unicité du couple (enseignant, couple) dans la base de donnée
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
            order='priority desc'
        )