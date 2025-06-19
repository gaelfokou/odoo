# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP
import datetime
import time
import re
import psycopg2
import logging

_logger = logging.getLogger(__name__)

class Student(models.Model):
    _name = 'oe.school.student'
    _inherit=['mail.thread', 'mail.activity.mixin',]
    _description = 'Gestion des étudiants'

    name = fields.Char(string="Nom(s) et prénom(s)", compute='_compute_name', store=True)
    last_name = fields.Char(string="Nom(s)", required=True)
    first_name = fields.Char(string="Prénom(s)")
    matricule = fields.Char(string="Matricule")
    student_enroll_ids = fields.One2many(
        'oe.school.student.enrollment',
        'student_id',
        string='Candidatures',
    )
    batch_id = fields.Many2one(
        'siantou.ems.core.student.batch',
        string='Lot de l\'étudiant',
    )
    school_id = fields.Many2one(
        'siantou.ems.core.school',
        string='Ecole',
    )
    cycle_id = fields.Many2one(
        'oe.school.course',
        string='Cursus ou Cycle',
    )
    region_id = fields.Many2one("siantou.ems.core.region", string="Région")
    city_id = fields.Many2one('siantou.ems.core.city', string="Ville")
    quarter_id = fields.Many2one('siantou.ems.core.quarter', string="Quartier")
    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        string='Filière',
        related='specialty_id.field_of_study_id',
        store=True
    )
    specialty_id = fields.Many2one(
        'siantou.ems.core.specialty',
        string='Spécialité',
        required=True
    )
    option_id = fields.Many2one(
        'siantou.ems.core.option',
        string='Option',
    )
    type_cour = fields.Selection([
            ('cj', 'Cours du jour'),
            ('cs', 'Cours du soir'),
        ],
        string='Type de cours',
        default='cj',
    )
    status_univ = fields.Selection([
            ('new', 'Nouveau'),
            ('old', 'Ancien'),
        ],
        string='Statut universitaire',
        default='old',
    )
    date_naissance = fields.Date(string="Date de naissance")
    lieu_naissance = fields.Char(string="Lieu de naissance")
    sexe = fields.Selection([
            ('masculin', 'Masculin'),
            ('feminin', 'Féminin'),
        ], string="Sexe"
    )
    situat_matri = fields.Selection([
        ('marie', 'Marié'),
        ('celibat', 'Célibataire'),
        ('concub', 'Concubinage'),
    ], string="Situation matrimoniale")
    nationalite = fields.Many2one(
        'siantou.ems.core.country',
        string="Nationalité(Pays d'origine)",
    )
    autre = fields.Char(string="Autre pays")
    is_autre_pays = fields.Boolean(string="Autre pays ?", default=False)
    lieu_residence = fields.Char(string="Lieu de résidence")
    email = fields.Char(string="E-mail")
    private_email = fields.Char(string="Adresse e-mail privée")
    private_phone = fields.Char(string="Numéro de téléphone privé")
    level_id = fields.Many2one(
        'siantou.ems.core.level',
        string="Niveau",
        required=True
    )
    year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année Académique',
        required=True,
        default=lambda self: self.env['siantou.ems.core.year'].search([('is_active', '=', True)], limit=1)
    )
    # payment_ids = fields.Many2one(
    #     "education.fee.payment",
    #     string="Paiements",
    #     readonly=True,
    #     default=lambda self: self.env['education.fee.payment'].search([('student_id', '=', self.id)], limit=1)
    # )
    user_id = fields.Many2one(
        'res.users',
        string="Utilisateur associé",
        help="Utilisateur associé à cet étudiant"
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Rest partner',
        related='user_id.partner_id',
        store=True
    )
    status_user = fields.Selection([
            ('new', 'Jamais connecté'),
            ('active', 'Confirmé'),
        ],
        string='Statut',
        related='user_id.state',
    )

    timetable_ids = fields.One2many(
        'siantou.ems.timetable.timetable',
        string="Emplois du temps",
        compute='_compute_timetables',
        store=False
    )

    class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe',
    )

    delegate_class_ids = fields.Many2many(
        'siantou.ems.core.class',
        'delegate_class_student_rel',
        'delegate_student_id',
        'delegate_class_id',
        string='Délégués de classe',
    )

    specialty_id_domain = fields.Binary(compute='_compute_school_domain', default=[])

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

    @api.depends('school_id')
    def _compute_school_domain(self):
        for record in self:
            domain = []
            if record.school_id.id:
                domain.append(('school_id', '=', record.school_id.id))
            if record.cycle_id.id:
                domain.append(('cycle_id', '=', record.cycle_id.id))
            field_of_study_ids = self.env['siantou.ems.core.field_of_study'].search(domain)
            domain = [
                ('field_of_study_id', 'in', field_of_study_ids.ids)
            ]
            record.specialty_id_domain = domain

    @api.onchange('school_id')
    def _onchange_school(self):
        for record in self:
            record.field_of_study_id = None
            record.level_id = None
            record.class_id = None
            record.specialty_id = None
            record.option_id = None

    @api.onchange('cycle_id')
    def _onchange_school(self):
        for record in self:
            record.field_of_study_id = None
            record.level_id = None
            record.class_id = None
            record.specialty_id = None
            record.option_id = None

    @api.onchange('level_id')
    def _onchange_level(self):
        for record in self:
            record.class_id = None

    @api.onchange('specialty_id')
    def _onchange_specialty(self):
        for record in self:
            record.class_id = None
            record.option_id = None

    @api.onchange('option_id')
    def _onchange_option(self):
        for record in self:
            record.class_id = None

    @api.depends('class_id')
    def _compute_timetables(self):
        # Recherche des emplois du temps qui correspondent à la filière et au niveau de l'étudiant
        for record in self:
            timetables = self.env['siantou.ems.timetable.timetable'].search([
                ('class_id', '=', record.class_id.id),
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

    def create_student_user(self, student):
        try:
            ecole = re.sub('[^A-Za-z]+', '', student.school_id.name)
            ecole = ecole[:4]
            ecole = ecole.upper()
            if not student.matricule or not student.matricule.strip():
                matricule = ecole + self.env['ir.sequence'].next_by_code('oe.school.student')
                while True:
                    student_id = self.env['oe.school.student'].search([
                        ('id', '!=', student.id),
                        ('matricule', '=', matricule),
                    ], limit=1)
                    if student_id:
                        matricule = ecole + self.env['ir.sequence'].next_by_code('oe.school.student')
                    else:
                        break
            else:
                matricule = student.matricule
                while True:
                    if matricule.find('2024') != -1:
                        matricule = matricule.replace('2024', '')
                    else:
                        break
                matricule = '{}2024'.format(matricule)
            password = matricule
            if student.email and student.email.strip():
                email = student.email
            else:
                last_name = student.last_name if student.last_name else ''
                while True:
                    if last_name.find('  ') != -1:
                        last_name = last_name.replace('  ', ' ')
                    else:
                        break
                last_name = last_name.strip()
                last_name = last_name.split(' ')
                first_name = student.first_name if student.first_name else ''
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
                # name = student.name
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
                        ('work_email', '=', email),
                    ], limit=1)
                    student_id = self.env['oe.school.student'].search([
                        ('id', '!=', student.id),
                        ('email', '=', email),
                    ], limit=1)
                    if res_user_id or employee_id or student_id:
                        i = i + 1
                        email = username + f'{i}' + '@siantou.net'
                    else:
                        break
            student.write({
                'matricule': matricule,
                'email': email,
            })
            student.student_enroll_ids.create({
                'year_id': student.year_id.id,
                'school_id': student.school_id.id,
                'cycle_id': student.cycle_id.id,
                'field_of_study_id': student.field_of_study_id.id,
                'specialty_id': student.specialty_id.id,
                'option_id': student.option_id.id,
                'class_id': student.class_id.id,
                'type_cour': student.type_cour,
                'status_univ': student.status_univ,
                'session_lieu_obt': student.lieu_residence,
                'dern_etab_freq': student.lieu_residence,
                'level_id': student.level_id.id,
                'batch_id': student.batch_id.id,
                'student_id': student.id,
            })
            user_id = self.env['res.users'].search([
                ('login', '=', email),
            ], limit=1)
            if user_id:
                user_id.unlink()
            group_id = self.env.ref('base.group_portal')
            user_id = self.env['res.users'].with_context(no_reset_password=True).create({
                'login': email,
                'name': student.name,
                'password' : password,
                'groups_id': [(6, 0, [group_id.id])],
            })
            # self.env.cr.commit()
        except psycopg2.errors.NotNullViolation as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except psycopg2.Error as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except Exception as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

    def action_create_student_user(self):
        student = self.env['oe.school.student'].search([
            ('id', '=', self.id),
        ], limit=1)
        if student:
            self.create_student_user(student)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_create_all_student_user(self):
        active_ids = self.env.context.get('active_ids', [])
        student_ids = self.env['oe.school.student'].browse(active_ids)
        for student in student_ids:
            self.create_student_user(student)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.model
    def create(self, vals):
        if 'email' in vals and vals['email'] and vals['email'].strip():
            student_id = self.env['oe.school.student'].search([('email', '=', vals['email'])], limit=1)
            if student_id:
                return None

        if 'name' in vals and vals['name'] and vals['name'].strip():
            if 'last_name' not in vals or not vals['last_name'] or not vals['last_name'].strip():
                vals['last_name'] = Student.get_last_name(vals['name'])
            if 'first_name' not in vals or not vals['first_name'] or not vals['first_name'].strip():
                vals['first_name'] = Student.get_first_name(vals['name'])

        specialty_id = self.env['siantou.ems.core.specialty'].browse(vals['specialty_id'])
        if specialty_id:
            vals['school_id'] = specialty_id.field_of_study_id.school_id.id

        student = super(Student, self).create(vals)

        self.create_student_user(student)

        return student

    def open_student_form(self):
        # return {
        #     'type': 'ir.actions.act_url',
        #     'url': 'https://odoo.com',
        #     'target': 'self',
        # }
        return {
            'name': 'Nouveau étudiant',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'oe.school.student',
            'target': 'new',
            'view_id': self.env.ref('siantou_ems_core.student_form_view').id,
            # 'context': {'active_id': self.id},
        }

    def open_data_request_wizard_form(self):
        # return {
        #     'type': 'ir.actions.act_url',
        #     'url': 'https://odoo.com',
        #     'target': 'self',
        # }
        return {
            'name': 'Données requises',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'siantou.ems.core.data_request_wizard',
            'target': 'new',
            'view_id': self.env.ref('siantou_ems_core.view_data_request_wizard').id,
            # 'context': {'active_id': self.id},
        }

    @api.model
    def get_students(self, domain=[]):
        students = self.env['oe.school.student'].search(domain)
        return students.read()

    def action_open_filter(self):
        view_id = self.env.ref('siantou_ems_core.student_filter_wizard').id
        return {
            'name': 'Filtre des étudiants',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'student.filter.wizard',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
        }

    def action_reset_filter(self):
        self.env['ir.config_parameter'].sudo().set_param(f'filter.{self.env.user.id}', '')
        action = self.env.ref('siantou_ems_core.action_show_student').read()[0]
        action.update({
            'target': 'main',
        })
        return action

    def action_print_pdf(self):
        active_ids = self.env.context.get('active_ids', [])
        students = self.env['oe.school.student'].browse(active_ids)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')
        report_data = self.env['student.print.wizard'].create({})
        domain = [
            ('id', 'in', active_ids)
        ]
        data = report_data.print_student_report_data(domain)

        # Appeler le rapport PDF
        if not data['docdata']['student_data']:
            raise UserError('Aucune donnée trouvée')
        report_action = self.env.ref('siantou_ems_core.action_report_student')
        return report_action.report_action(self, data=data)

class StudentCareer(models.Model):
    _name = 'oe.school.student.career'
    _description = 'Gestion du parcours des étudiants'

    name = fields.Char(string="Libellé", required=True)
    student_id = fields.Many2one(
        'oe.school.student',
        string='Étudiant',
        ondelete='cascade',
        required=True
    )
    year_id = fields.Many2one(
        "siantou.ems.core.year",
        string="Année académique",
        required=True
    )
    level_id = fields.Many2one("siantou.ems.core.level", string="Niveau", required=True)
    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        string='Filière',
        required=True,
    )
    cycle_id = fields.Many2one(
        'oe.school.course',
        string='Cursus ou Cycle',
        required=True
    )
    observations = fields.Html(string="Observations")