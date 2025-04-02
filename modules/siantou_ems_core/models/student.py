# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, tools, _

import datetime
import time
import logging
import re
import psycopg2

_logger = logging.getLogger(__name__)

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError, UserError
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP

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
    partner_id = fields.Many2one(
        'res.partner',
        string='Rest partner',
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
        required=True
    )
    region_id = fields.Many2one("siantou.ems.core.region", string="Région")
    city_id = fields.Many2one("siantou.ems.core.city", string="Ville")
    quarter_id = fields.Many2one("siantou.ems.core.quarter", string="Quartier")
    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        string='Filière',
        required=True
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
        string="Type de cours",
        default='cj',
    )
    status_univ = fields.Selection([
            ('new', 'Nouveau'),
            ('old', 'Ancien'),
        ],
        string='Statut universitaire',
        default='old',
    )
    redoublant = fields.Selection(
        [
            ('oui', 'Oui'),
            ('non', 'Non')
        ],
        'Redoublant?',
        default="non"
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
    num_tel = fields.Char(string="N° de Téléphone")
    level_id = fields.Many2one(
        'siantou.ems.core.level',
        string="Niveau",
        required=True
    )
    year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année Académique',
        required=True,
        default=lambda self: self.env['siantou.ems.core.year'].search([('active', '=', True)], limit=1)
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
        compute="_compute_timetables",
        store=False
    )

    class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe',
    )

    @api.onchange('cycle_id')
    def _onchange_school(self):
        for record in self:
            record.field_of_study_id = None
            record.level_id = None
            record.class_id = None
            record.specialty_id = None
            record.option_id = None

    @api.onchange('field_of_study_id')
    def _onchange_field_of_study(self):
        for record in self:
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

    @api.depends('field_of_study_id', 'specialty_id', 'option_id', 'level_id')
    def _compute_timetables(self):
        # Recherche des emplois du temps qui correspondent à la filière et au niveau de l'étudiant
        for student in self:
            timetables = self.env['siantou.ems.timetable.timetable'].search([
                ('field_of_study_id', '=', student.field_of_study_id.id),
                ('specialty_id', '=', student.specialty_id.id),
                ('option_id', '=', student.option_id.id),
                ('level_id', '=', student.level_id.id)
            ])

            # Affecter les emplois du temps trouvés à l'attribut timetable_ids
            student.timetable_ids = timetables

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
                student_id = self.env['oe.school.student'].search([
                    ('id', '!=', student.id),
                    ('email', '=', email),
                ], limit=1)
                if res_user_id or student_id:
                    i = i + 1
                    email = username + f'{i}' + '@siantou.net'
                else:
                    break
            partner_id = self.env['res.partner'].create({
                'name': student.name,
                'email': email,
                'phone': student.num_tel,
                'is_company': False,
            })
            group_id = self.env.ref('base.group_portal')
            user_id = self.env['res.users'].with_context(no_reset_password=True).create({
                'login': email,
                'name': student.name,
                'password' : password,
                'partner_id': partner_id.id,
                'groups_id': [(6, 0, [group_id.id])],
            })
            student.write({
                'matricule': matricule,
                'email': email,
                'user_id': user_id.id,
                'partner_id': partner_id.id,
            })
            student.student_enroll_ids.create({
                'year_id': student.year_id.id,
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
                'student_id': student.id,
            })
            self.env.cr.commit()
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
        field_of_study_id = self.env['siantou.ems.core.field_of_study'].search([('id', '=', vals['field_of_study_id'])], limit=1)
        if field_of_study_id:
            vals['school_id'] = field_of_study_id.school_id.id

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

    @api.model
    def get_students(self):
        students = self.env['oe.school.student'].search([])
        # we can add the students to the dashboard
        return students.read()

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