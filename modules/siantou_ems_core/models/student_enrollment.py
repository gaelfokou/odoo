# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import time
import logging

from psycopg2 import sql, DatabaseError


from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError, UserError
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP


_logger = logging.getLogger("++++++++++++")

class StudentEnrollment(models.Model):
    _name = 'oe.school.student.enrollment'
    _inherit=['mail.thread', 'mail.activity.mixin',]
    _description = 'Student Enrollment'


    partner_id = fields.Many2one(
        'res.partner',
        string='Employé',
    )

    name = fields.Char(
        string="Nom(s) et prénom(s)", 
        required=True,
        index=True,
        translate=True,
        help="Nom(s) et prénom(s) du(des) étudiant(s).",
        track_visibility='onchange'
    )
    matricule = fields.Char(string="Matricule")
    code_enrol = fields.Char(string="Code de préinscription", required=True)
    cycle_id = fields.Many2one(
        'oe.school.course',
        string='Cycle',
        required=True
    )
    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        string='Filière ',
        required=True,
    )
    type_cour = fields.Selection([
        ('cj', 'Cours du jour'),
        ('cs', 'Cours du soir'),
    ], required=True, string="Type de cours",)
    status_univ = fields.Selection([
        ('new', 'Nouveau'),
        ('red', 'Redoublant'),
    ], required=True, string="Statut universitaire")
    nbre_matiere= fields.Integer(string="Nombre de matière")
    date_naissance = fields.Date(string="Date de naissance", required=True)
    lieu_naissance = fields.Char(string="Lieu de naissance", required=True)
    sexe = fields.Selection([
        ('masculin', 'Masculin'),
        ('feminin', 'Féminin'),
    ], required=True, string="Sexe")
    situat_matri = fields.Selection([
        ('marie', 'Marié'),
        ('celibat', 'Célibataire'),
        ('concub', 'Concubinage'),
    ], string="Situation matrimoniale", required=True)
    nationalite = fields.Many2one(
        'siantou.ems.core.country',
        string="Nationalité(Pays d'origine)",
        required=True,
    )

    region_id = fields.Many2one("siantou.ems.core.region", string="Région")
    city_id = fields.Many2one("siantou.ems.core.city", string="Ville")
    quarter_id = fields.Many2one("siantou.ems.core.quarter", string="Quartier")

    autre = fields.Char(string="Autre pays")
    lieu_residence = fields.Char(string="Lieu de résidence", required=True)
    email = fields.Char(string="E-mail", required=True)
    num_tel = fields.Char(string="N° de Téléphone", required=True)
    dipl_req_ids = fields.Many2many('oe.school.course.degree', string="Diplôme requis", required=True)
    session_lieu_obt = fields.Char(string="Session et lieu d'obtention", required=True)
    dern_etab_freq = fields.Char(string="Dernier établissement fréquenté", required=True)
    annee_acad = fields.Char(string="Année académique", required=True)
    level_id = fields.Many2one("siantou.ems.core.level", string="Niveau", required=True)
    full_name_tutor = fields.Char(string="Nom(s) et prénom(s)", required=True)
    num_tel_tutor = fields.Char(string="N° de Téléphone", required=True)
    date_preins = fields.Datetime(string="Date de préinscription", default=datetime.datetime.now())
    status = fields.Selection([
            ('broui', 'Brouillon'),
            ('inscrip', 'Inscrit'),
            # ('rej', 'Rejeter'),
            ('transfer', 'Transféré'),
        ],
        string="Status", 
        default="broui", 
        track_visibility='onchange'
    )

    observations = fields.Html(string="Observations")


    # model = fields.Char('Related Document Model')
    # res_id = fields.Many2oneReference('Related Document ID', model_field='model')
    
    # school_name = fields.Char('School Name', required=True)
    # course_name = fields.Char('Program/Course', required=True)
    # date_start = fields.Date('Start Date', required=True)
    # date_end = fields.Date('End Date', required=True)
    # status = fields.Selection([
    #     ('enroll', 'Enrôllé'),
    #     ('complete', 'Complété'),
    #     ('transfer', 'Transférré'),
    #     ('withdrawn', 'Brouillon'),
    #     ('suspended', 'Suspendu'),
    #     ('other', 'Other'),
    # ], string='Statut')
    # transcript_detail = fields.Text('Rélevé de note')
    # reason = fields.Text(string='Raison du départ')
    # address_school = fields.Text('Adresse de l\'école')
    
    # def compute_inscrire(self):
    #     self.status = 'inscrip'

    # def name_get(self):
    #     result = []
    #     for record in self:
    #         # Customize the display name format
    #         display_name = f"{record.full_name}"
    #         result.append((record.id, display_name))
    #     return result


    def action_preinscrip_wizard(self):
        action = self.env.ref('siantou_ems_core.action_fee_enrollment_wizard').read()[0]
        action.update({
            'name': f"Frais d'inscription",
            'res_model': 'siantou.ems.core.fee.enrollment.student',
            'type': 'ir.actions.act_window',
        })
        return action


    def action_admission_enrollment_wizard(self):
        action = self.env.ref('siantou_ems_core.action_student_admission_enrollment_wizard').read()[0]
        action.update({
            'name': f"Terminer l'inscription de {self.name}",
            'res_model': 'siantou.ems.core.student.enrollment.admission.wizard',
            'type': 'ir.actions.act_window',
        })
        return action


   



    def compute_rejected(self):
        self.status='preinscrip'
        student_enrol = self.env['oe.school.student.enrollment'].sudo().search([('name', '=', self.name)], limit=1)
        student = self.env['oe.school.student.enrollment'].sudo().search([('name', '=', self.name)], limit=1)
        student.unlink()
        student_enrol.unlink()



class StudentEnrollmentAdmission(models.Model):
    _name = 'oe.school.student.enrollment.admission'
    _description = 'Admission scolarité des étudiants'

    student_enrollemnt_id = fields.Many2one(
        'oe.school.student.enrollment', 
        string="Etudiant préinscrit", 
        # required=True,    
    )
    observations = fields.Html(string="Observations", required=True)








