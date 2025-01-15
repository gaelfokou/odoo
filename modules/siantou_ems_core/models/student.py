
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, api

import datetime
import time
import logging

from psycopg2 import sql, DatabaseError

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
        # required=True
    )
    batch_id = fields.Many2one(
        'siantou.ems.core.student.batch',
        string='Lot de l\'étudiant',
    )
    school_id = fields.Many2one(
        'siantou.ems.core.school',
        string='Ecole',
        # required=True
    )
    cycle_id = fields.Many2one(
        'oe.school.course',
        string='Cycle',
        required=True
    )
    region_id = fields.Many2one("siantou.ems.core.region", string="Région")
    city_id = fields.Many2one("siantou.ems.core.city", string="Ville")
    quarter_id = fields.Many2one("siantou.ems.core.quarter", string="Quartier")
    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        string='Filière',
        required=True,
    )
    specialty_id = fields.Many2one(
        'siantou.ems.core.specialty',
        string='Spécialité',
        required=True,
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
    level_id = fields.Many2one("siantou.ems.core.level", string="Niveau", required=True)
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
    
    @api.depends('field_of_study_id', 'level_id')
    def _compute_timetables(self):
        """Méthode pour récupérer les emplois du temps en fonction de la filière et du niveau"""
        Timetable = self.env['siantou.ems.timetable.timetable']
    
        # Recherche des emplois du temps qui correspondent à la filière et au niveau de l'étudiant
        for student in self:
            timetables = Timetable.search([
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
        students = self.env['oe.school.student'].sudo().search([])  
        # _logger.info(f"Matricule généré : {len(students)}")
        nbre = len(students) + 1
        matricule = f"{last_caract_year}{field_of_study_id.school_id.code}000{nbre}"
        _logger.info(f"Matricule généré : {matricule}")
        return matricule


    def action_create_portal_user(self):
        """Crée un compte utilisateur portail pour l'étudiant"""
         
        for student in self:
            partner_id = student.student_enroll_id.partner_id
            # Création de l'email
            email = student.name.replace(' ', '.').lower() + '@siantou.net'
            if not partner_id:
                partner_id = student.env['res.partner'].create({
                    'name': student.name,
                    'email': email,
                    'phone': student.num_tel,
                    'is_company': False,
                })
            if not student.user_id:
                # Création du mot de passe
                password = student.name.replace(' ', '.').lower()
                user_vals = {
                    'name': student.name,
                    'login': email,
                    'email': email,
                    'password': password,
                    'partner_id': partner_id.id,
                    'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
                }
                user = self.env['res.users'].create(user_vals)
                student.user_id = user
                _logger.info(user.email)
            


    @api.model
    def create(self, vals):
        field_of_study_id = self.env['siantou.ems.core.field_of_study'].browse(vals['field_of_study_id'])
        batch = self.env['siantou.ems.core.student.batch'].assign_batch(
            field_of_study_id.school_id.id, 
            field_of_study_id.id, 
            vals['level_id']
        )
        vals['batch_id'] = batch.id
        vals['matricule'] = self.generate_matricule(field_of_study_id)

        # Création de l'étudiant
        student = super().create(vals)
        
        # Appel de la fonction action_create_portal_user pour créer automatiquement un compte utilisateur
        student.action_create_portal_user()
        
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