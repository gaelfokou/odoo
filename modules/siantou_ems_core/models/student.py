
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, api

import datetime
import time
import logging
import re
import psycopg2

_logger = logging.getLogger("++++++++++++")

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError, UserError
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP




# class Student(models.Model):
#     _inherit = 'res.partner'

#     is_student = fields.Boolean(
#         string='Est un étudiant',
#         default=False
#     )


class Student(models.Model):
    _name = 'oe.school.student'
    _inherit=['mail.thread', 'mail.activity.mixin',]
    _description = 'Gestion des étudiants'
    
    name = fields.Char(string="Nom(s) et prénom(s)", required=True)
    matricule = fields.Char(string="Matricule")
    student_enroll_id = fields.Many2one(
        'oe.school.student.enrollment',
        string='Etudiant(Préinscription)',
        ondelete='cascade',
        required=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Rest partner',
        related='student_enroll_id.partner_id',
    )
    batch_id = fields.Many2one(
        'siantou.ems.core.student.batch',
        string='Lot de l\'étudiant',
    )
    school_id = fields.Many2one(
        'siantou.ems.core.school',
        string='Ecole',
        related='field_of_study_id.school_id'
        # required=True
    )
    cycle_id = fields.Many2one(
        'oe.school.course',
        string='Cycle',
        required=True,
        related='class_id.filiere_id.cursus_id'
    )
    region_id = fields.Many2one("siantou.ems.core.region", string="Région")
    city_id = fields.Many2one("siantou.ems.core.city", string="Ville")
    quarter_id = fields.Many2one("siantou.ems.core.quarter", string="Quartier")
    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        string='Filière',
        required=True,
        related='class_id.filiere_id'
    )
    specialty_id = fields.Many2one(
        'siantou.ems.core.specialty',
        string='Spécialité',
        required=True
        # related='class_id.specialte_id'
    )
    type_cour = fields.Selection([
        ('cj', 'Cours du jour'),
        ('cs', 'Cours du soir'),
    ], required=True, string="Type de cours",)
    status_univ = fields.Selection([
            ('new', 'Nouveau'),
            ('red', 'Ancien'),
        ], required=True, 
        default='red',
        string="Statut universitaire"
    )
    redoublant = fields.Selection(
        [
            ('oui', 'OUI'), 
            ('non', 'NON')
        ],
        'Redoublant?',
        default="non"
    )
    date_naissance = fields.Date(string="Date de naissance", required=True)
    lieu_naissance = fields.Char(string="Lieu de naissance", required=True)
    sexe = fields.Selection([
            ('masculin', 'Masculin'),
            ('feminin', 'Féminin'),
        ], required=True, string="Sexe"
    )
    situat_matri = fields.Selection([
        ('marie', 'Marié'),
        ('celibat', 'Célibataire'),
        ('concub', 'Concubinage'),
    ], string="Situation matrimoniale", required=True)
    nationalite = fields.Many2one(
        'siantou.ems.core.country',
        string="Nationalité(Pays d'origine)",
    )
    autre = fields.Char(string="Autre pays")
    is_autre_pays = fields.Boolean(string="Autre pays ?", default=False)
    lieu_residence = fields.Char(string="Lieu de résidence", required=True)
    email = fields.Char(string="E-mail", required=True)
    num_tel = fields.Char(string="N° de Téléphone", required=True)
    level_id = fields.Many2one(
        'siantou.ems.core.level',
        string="Niveau",
        required=True,
        related='class_id.niveau_id'
    )
    annee_acad_current = fields.Many2one(
        "siantou.ems.core.year", 
        string="Année académique", 
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
        string="Utilisateur lié",
        readonly=True,
        help="Compte utilisateur portail associé à cet étudiant"
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
        required=True
    )


    @api.depends('field_of_study_id', 'level_id')
    def _compute_timetables(self):
        # Recherche des emplois du temps qui correspondent à la filière et au niveau de l'étudiant
        for student in self:
            timetables = self.env['siantou.ems.timetable.timetable'].search([
                ('field_of_study_id', '=', student.field_of_study_id.id),
                ('level_id', '=', student.level_id.id)
            ])
            
            # Affecter les emplois du temps trouvés à l'attribut timetable_ids
            student.timetable_ids = timetables

    def generate_matricule(self, field_of_study_id):
        # Get the current year
        current_year = datetime.datetime.now().year
        last_caract_year = str(current_year)[2:]
        # _logger.info(f"last_caract_year : {last_caract_year}")
        students = self.env['oe.school.student'].search([])  
        # _logger.info(f"Matricule généré : {len(students)}")
        nbre = len(students) + 1
        matricule = f"{last_caract_year}{field_of_study_id.school_id.code}000{nbre}"
        _logger.info(f"Matricule généré : {matricule}")
        return matricule

    def create_student_user(self, student):
        try:
            ecole = re.sub('[^A-Za-z]+', '', student.field_of_study_id.school_id.name)
            ecole = ecole[:4]
            ecole = ecole.upper()
            matricule = ecole + self.env['ir.sequence'].next_by_code('oe.school.student')
            if not student.matricule or not student.matricule.strip():
                while True:
                    student_id = self.env['oe.school.student'].search([
                        ('matricule', '=', matricule),
                    ], limit=1)
                    if student_id:
                        matricule = ecole + self.env['ir.sequence'].next_by_code('oe.school.student')
                    else:
                        student.write({
                            'matricule': matricule,
                        })
                        break
            else:
                matricule = student.matricule
                while True:
                    if matricule.find('2024') != -1:
                        matricule = matricule.replace('2024', '')
                    else:
                        break
                matricule = '{}2024'.format(matricule)
                student.write({
                    'matricule': matricule,
                })
            password = matricule
            name = student.name
            name = name.strip()
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
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
            student_enroll_id = student.student_enroll_id
            if not student_enroll_id:
                partner_id = self.env['res.partner'].create({
                    'name': student.name,
                    'email': email,
                    'phone': student.num_tel,
                    'is_company': False,
                })
                diplo_requis = self.env['oe.school.course.degree'].search([('cursus_id', '=', student.cycle_id.id)])
                diplo_requis_ids = diplo_requis.ids
                if len(diplo_requis_ids) == 0:
                    diplo_requis = self.env['oe.school.course.degree'].search([
                        ('name', '=', student.cycle_id.name),
                        ('cursus_id', '=', student.cycle_id.id),
                    ])
                    diplo_requis_ids = diplo_requis.ids
                    if len(diplo_requis_ids) == 0:
                        diplo_requis = self.env['oe.school.course.degree'].create({
                            'name': student.cycle_id.name,
                            'cycle_id': student.cycle_id.id,
                        })
                        diplo_requis_ids.append(diplo_requis.id)
                student_enroll_id = self.env['oe.school.student.enrollment'].create({
                    'name': student.name,
                    'email': email,
                    'num_tel': student.num_tel,
                    'year_id': student.annee_acad_current.id,
                    'cycle_id': student.cycle_id.id,
                    'field_of_study_id': student.field_of_study_id.id,
                    'specialty_id': student.specialty_id.id,
                    'type_cour': student.type_cour,
                    'status_univ': student.status_univ,
                    'date_naissance': student.date_naissance,
                    'lieu_naissance': student.lieu_naissance,
                    'sexe': student.sexe,
                    'situat_matri': student.situat_matri,
                    'lieu_residence': student.lieu_residence,
                    'dipl_req_ids': diplo_requis_ids,
                    'session_lieu_obt': student.lieu_residence,
                    'dern_etab_freq': student.lieu_residence,
                    'annee_acad': student.annee_acad_current.name,
                    'level_id': student.level_id.id,
                    'full_name_tutor': student.name,
                    'num_tel_tutor': student.num_tel,
                    'partner_id': partner_id.id,
                })
            else:
                partner_id = student_enroll_id.partner_id
            if not partner_id:
                partner_id = self.env['res.partner'].create({
                    'name': student.name,
                    'email': email,
                    'phone': student.num_tel,
                    'is_company': False,
                })
                student_enroll_id.write({
                    'partner_id': partner_id.id,
                })
            user_id = self.env['res.users'].search([
                ('partner_id', '=', partner_id.id),
            ], limit=1)
            if not user_id:
                i = 0
                while True:
                    user_id = self.env['res.users'].search([
                        ('login', '=', email),
                    ], limit=1)
                    if user_id:
                        i = i + 1
                        email = username + f'.{i}' + '@siantou.net'
                    else:
                        student_id = self.env['oe.school.student'].search([
                            ('id', '!=', student.id),
                            ('email', '=', email),
                        ], limit=1)
                        if student_id:
                            i = i + 1
                            email = username + f'.{i}' + '@siantou.net'
                        else:
                            break
                group_id = self.env.ref('base.group_portal')
                user_id = self.env['res.users'].create({
                    'login': email,
                    'name': name,
                    'password' : password,
                    'partner_id': partner_id.id,
                    'groups_id': [(6, 0, [group_id.id])],
                })
            else:
                i = 0
                while True:
                    user_id = self.env['res.users'].search([
                        ('login', '=', email),
                    ], limit=1)
                    if user_id:
                        i = i + 1
                        email = username + f'.{i}' + '@siantou.net'
                    else:
                        student_id = self.env['oe.school.student'].search([
                            ('id', '!=', student.id),
                            ('email', '=', email),
                        ], limit=1)
                        if student_id:
                            i = i + 1
                            email = username + f'.{i}' + '@siantou.net'
                        else:
                            break
            partner_id.write({
                'email': email,
            })
            user_id.write({
                'login': email,
            })
            student.write({
                'name': name,
                'email': email,
                'user_id': user_id.id,
            })
        except psycopg2.errors.NotNullViolation as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
            raise ValidationError("L'adresse e-mail professionnelle n'est pas renseignée.")
        except psycopg2.Error as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except Exception as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

    def action_create_portal_user(self):
        for student in self:
            self.create_student_user(student)

    @api.model
    def create(self, vals):
        class_id = self.env['siantou.ems.core.class'].browse(vals['class_id'])
        field_of_study_id = class_id.filiere_id
        batch = self.env['siantou.ems.core.student.batch'].assign_batch(
            field_of_study_id.school_id.id, 
            field_of_study_id.id, 
            class_id.niveau_id.id
        )
        vals['batch_id'] = batch.id
        # vals['matricule'] = self.generate_matricule(field_of_study_id)

        # Création de l'étudiant
        student = super().create(vals)

        self.create_student_user(student)
        
        return student



class StudentCareer(models.Model):
    _name = 'oe.school.student.career'
    _description = 'Gestion du parcours des étudiants'
    

    name = fields.Char(string="Libellé", required=True)
    student_id = fields.Many2one(
        'oe.school.student',
        string='Etudiant',
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
        string='Cycle',
        required=True
    )
    observations = fields.Html(string="Observations")