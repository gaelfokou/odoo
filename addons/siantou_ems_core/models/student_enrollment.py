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


class StudentEnrollment(models.Model):
    _name = 'oe.school.student.enrollment'
    _description = 'Student Enrollment'

    full_name = fields.Char(string="Nom(s) et prénom(s)", required=True)
    matricule = fields.Char(string="Matricule")
    cycle_id = fields.Many2one(
        'oe.school.course',
        string='Cycle',
        required=True
    )
    specialite_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        string='Spécialité ',
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
    nationalite = fields.Selection([
        ('cam', 'Cameroun'),
        ('rep_centr', 'République centrafricaine'),
        ('tchad', 'Tchad'),
        ('cong_braz', 'Congo-Brazzaville(République du Congo)'),
        ('cong_kins', 'Congo-Kinshasa(République démocratique du Congo)'),
        ('gabon', 'Gabon'),
        ('guin_equat', 'Guinée équatoriale'),
        ('sao_t', 'Sao Tomé-et-Principe'),
        ('autre', 'Autre pays'),
    ],string="Nationalité", required=True)
    autre = fields.Char(string="Autre pays")
    lieu_residence = fields.Char(string="Lieu de résidence", required=True)
    email = fields.Char(string="E-mail", required=True)
    num_tel = fields.Char(string="N° de Téléphone", required=True)
    dipl_req_ids = fields.Many2many('oe.school.course.degree', string="Diplôme requis", required=True)
    session_lieu_obt = fields.Char(string="Session et lieu d'obtention", required=True)
    dern_etab_freq = fields.Char(string="Dernier établissement fréquenté", required=True)
    annee_acad = fields.Char(string="Année académique", required=True)
    niveau_id = fields.Many2one("siantou.ems.core.level", string="Niveau", required=True)
    full_name_tutor = fields.Char(string="Nom(s) et prénom(s)", required=True)
    num_tel_tutor = fields.Char(string="N° de Téléphone", required=True)
    date_preins = fields.Datetime(string="Date de préinscription", default=datetime.datetime.now())
    status = fields.Selection([
        ('broui', 'Brouillon'),
        ('preinscrip', 'Préinscrit'),
        ('inscrip', 'Inscription'),
    ],string="Status", default="broui")


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

    def compute_preinscrip(self):
        self.status = 'preinscrip'
