# -*- coding: utf-8 -*-

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

    # Variable booléenne pour identifier un portail
    is_portal = fields.Boolean(
        'Accéder au portail enseignant',
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
        'siantou.ems.timetable.timetable',
        string='Emplois du temps',
        compute='_compute_timetables',
        store=False
    )

    birthday = fields.Date(
        string='Date de naissance',
    )

    has_ir = fields.Boolean(
        'Droit IR',
        default=True,
    )

    has_apecus = fields.Boolean(
        'Droit APECUS',
        default=True,
    )

    has_cnps = fields.Boolean(
        'Droit CNPS',
        default=False,
    )

    has_allowance_cd = fields.Boolean(
        'Droit prime chef de département',
        default=False,
    )

    has_allowance_co = fields.Boolean(
        'Droit prime coordonnateur',
        default=False,
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

    @api.constrains('weekly_hours_limit')
    def _check_weekly_hours_limit_permanent(self):
        for record in self:
            if record.is_permanent and record.weekly_hours_limit != 24:
                raise ValidationError("Vous devez définir le quota horaire hebdommadaire de cours pour un enseignant permanent à 24")

    @api.depends('is_teacher')
    def _compute_timetables(self):
        # Recherche des emplois du temps qui correspondent à l'enseignant
        for record in self:
            timetables = self.env['siantou.ems.timetable.timetable'].search([
                ('employee_id', '=', record.id),
                '|',
                '&',
                ('group_id.is_active', '=', True),
                ('group_id.is_submit', '=', False),
                '&',
                ('group_parent_id.is_active', '=', True),
                ('group_parent_id.is_submit', '=', False),
            ])

            # Affecter les emplois du temps trouvés à l'attribut timetable_ids
            record.timetable_ids = timetables

    @api.onchange('is_teacher')
    def _onchange_timetables(self):
        # Recherche des emplois du temps qui correspondent à l'enseignant
        for record in self:
            timetables = self.env['siantou.ems.timetable.timetable'].search([
                ('employee_id', '=', record.id),
                '|',
                '&',
                ('group_id.is_active', '=', True),
                ('group_id.is_submit', '=', False),
                '&',
                ('group_parent_id.is_active', '=', True),
                ('group_parent_id.is_submit', '=', False),
            ])

            # Affecter les emplois du temps trouvés à l'attribut timetable_ids
            record.timetable_ids = timetables

    @staticmethod
    def get_last_name(x):
        while True:
            if x.find('  ') != -1:
                x = x.replace('  ', ' ')
            else:
                break
        x = x.strip()
        x = x.split(' ')
        if len(x) > 2:
            x = ' '.join(x[:2])
        elif len(x) == 2:
            x = ' '.join(x[:1])
        else:
            x = x[0]
        return x

    @staticmethod
    def get_first_name(x):
        while True:
            if x.find('  ') != -1:
                x = x.replace('  ', ' ')
            else:
                break
        x = x.strip()
        x = x.split(' ')
        if len(x) > 2:
            x = ' '.join(x[2:])
        elif len(x) == 2:
            x = ' '.join(x[1:])
        else:
            x = ''
        return x

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
                identifier = '{}'.format(identifier)
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
                    student_id = self.env['oe.school.student'].search([
                        ('email', '=', email),
                    ], limit=1)
                    if res_user_id or employee_id or student_id:
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

    def update_employee_identifier(self, employee):
        try:
            ecole = 'IUS'
            ecole = ecole[:4]
            ecole = ecole.upper()
            m = re.search(f'{ecole}(\\w+)2024', employee.identifier)
            if m:
                found = m.group(1)
                identifier = ecole + found
                employee.write({
                    'identifier': identifier,
                })
                if employee.user_id.id:
                    password = identifier
                    employee.user_id.write({
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
            exist_subject_ids = list(set(exist_subject_ids))
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
        if 'work_email' in vals and vals['work_email'] and vals['work_email'].strip():
            employee_id = self.env['hr.employee'].search([('work_email', '=', vals['work_email'])], limit=1)
            if employee_id:
                return None

        if 'name' in vals and vals['name'] and vals['name'].strip():
            if 'last_name' not in vals or not vals['last_name'] or not vals['last_name'].strip():
                vals['last_name'] = HrEmployee.get_last_name(vals['name'])
            if 'first_name' not in vals or not vals['first_name'] or not vals['first_name'].strip():
                vals['first_name'] = HrEmployee.get_first_name(vals['name'])

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
        employee_ids = list(employee_ids)
        for employee in employee_ids:
            self.create_employee_user(employee)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_update_all_employee_identifier(self):
        active_ids = self.env.context.get('active_ids', [])
        employee_ids = self.env['hr.employee'].browse(active_ids)
        employee_ids = list(employee_ids)
        for employee in employee_ids:
            self.update_employee_identifier(employee)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

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
            'context': {
                'default_year_id': self.env['siantou.ems.core.year'].search([('is_active', '=', True)], limit=1).id,
            },
        }

    def action_reset_filter(self):
        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', '')
        action = self.env.ref('siantou_ems_core.action_show_teacher').read()[0]
        action.update({
            'target': 'main',
        })
        return action

    def action_print_pdf(self):
        active_ids = self.env.context.get('active_ids', [])
        teachers = self.env['hr.employee'].browse(active_ids)
        teachers = list(teachers)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')
        report_data = self.env['teacher.print.wizard'].create({})
        domains = [
            ('id', 'in', active_ids)
        ]
        data = report_data.print_teacher_report_data(domains=domains)

        # Appeler le rapport PDF
        if len(data['docdata']['teacher_data']) == 0:
            raise UserError('Aucune donnée trouvée')
        report_action = self.env.ref('siantou_ems_core.action_report_teacher')
        return report_action.report_action(self, data=data)

    @api.model
    def get_data_group(self):
        data_group = {}
        data_group['has_group_dashboard'] = self.env.user.has_group('siantou_ems_core.group_dashboard')
        return data_group

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
        string='Cours',
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

    _sql_constraints = [
        ('unique_teacher_subject', 'unique(employee_id, subject_id)', 'Un enseignant ne peut être lié à un même cours qu\'une seule fois.')
    ]

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
