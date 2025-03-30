# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import time
import logging

from psycopg2 import sql, DatabaseError

from odoo import models, fields, api, tools, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError, UserError
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP

_logger = logging.getLogger(__name__)

class StudentEnrollment(models.Model):
    _name = 'oe.school.student.enrollment'
    _inherit=['mail.thread', 'mail.activity.mixin']
    _description = 'Gestion des inscriptions des étudiants'

    partner_id = fields.Many2one(
        'res.partner',
        string='Res partner',
    )
    registre_id = fields.Many2one(
        'siantou.session.registre', 
        "Registre d'admission" ,
        # domain="[('state', '=', 'application')]",
        # required=True
    )
    year_id = fields.Many2one(
        "siantou.ems.core.year", 
        string="Année académique", 
        required=True,
        default=lambda self: self.env['siantou.ems.core.year'].search([('active', '=', True)], limit=1)
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
    code_enrol = fields.Char(string="Code de préinscription", default="001485KOPLL")
    cycle_id = fields.Many2one(
        'oe.school.course',
        string='Cycle',
        required=True
    )
    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        string='Filière',
        required=True,
    )
    specialty_id = fields.Many2one(
        'siantou.ems.core.specialty',
        string='Spécialité',
    )
    option_id = fields.Many2one(
        'siantou.ems.core.option',
        string='Option',
    )
    class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe',
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
            # ('broui', "En attente de paiement des frais d'inscription"),
            ('inscrip', 'Inscrit'),
            ('rej', 'Candidature rejeté'),
            ('transfer', 'Candidature accepté'),
        ],
        string="Status",
        default="inscrip",
        track_visibility='onchange'
    )
    is_autre_pays = fields.Boolean(string="Autre pays ?", default=False)
    observations = fields.Html(string="Observations")
    file_ids = fields.Many2many(
        'ir.attachment',
        string="Attachment"
    )
    student_id = fields.Many2one(
        'oe.school.student',
        string='Étudiant',
        ondelete='cascade',
    )

    def print_payement_student(self):
        for rec in self:
            payment_id = self.env['education.fee.payment.enrollment'].search(
                [
                    ('student_id','=',rec.id),
                    ('year_id','=',rec.year_id.id),
                ], 
                limit=1
            )
            data = {
                # 'ids':rec.ids,
                'model':rec,
                'payment_id':{
                    'name':payment_id.name,
                    'year':payment_id.year_id.name,
                    'year':payment_id.year_id.name,
                },
                'student':{
                    'name':rec.name,
                    'code_enrol':rec.code_enrol,
                    'level':rec.level_id.name,
                    'field_of_study':rec.field_of_study_id.name,
                },
                'date': fields.date.today(),
                'facture': {
                    'name':f"INSCRIPTION {rec.field_of_study_id.name} {rec.level_id.name}",
                    'amount':payment_id.amount,
                    'date_payment':payment_id.date_payment,
                    'currency_id':payment_id.currency_id.name,
                },
            }

            _logger.info(data)
            #=====>>>>> Appeler le rapport PDF
            report_action = self.env.ref('siantou_ems_core.action_report_student_core_pdf')
            return report_action.report_action(self,data=data)

    @api.onchange('nationalite')
    def onchange_nationalite(self):
        if self.nationalite:
            self.is_autre_pays=False
            self.autre=""

    def action_preinscrip_wizard(self):
        action = self.env.ref('siantou_ems_core.action_fee_enrollment_wizard').read()[0]
        action.update({
            'name': f"Encaissement des frais d'inscription de Mr/Mdme {self.name} / {self.field_of_study_id.name} / {self.level_id.name}",
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
        self.status='rej'

    @api.model
    def create(self, values):
        result = super().create(values)
        _logger.info(result.name)
        partner_id = self.env['res.partner'].create({
            "name":values['name']
        })
        result.partner_id = partner_id.id
        return result

# class StudentEnrollmentFileAdmission(models.Model):
#     _name = 'oe.school.student.enrollment.file'
#     _description = "Gestion des fichiers d'enrollement des étudiants"

#     student_enrollemnt_id = fields.Many2one(
#         'oe.school.student.enrollment', 
#         string="Étudiant préinscrit", 
#         required=True,    
#     )
#     submitted_date = fields.Date(
#         string="Date de dépôt", 
#         default=datetime.date.today(),
#         help="Documents soumis le"
#     )
#     doc_attachment_id = fields.Many2many(
#         'ir.attachment', 'doc_attach_rel',
#         'doc_id', 'attachment_id',
#         string="Pièces Jointes",
#         help='You can attach the copy of your document',
#         copy=False
#     )

# class IrAttachment(models.Model):
#     _inherit = 'ir.attachment'

#     doc_attach_rel = fields.Many2many(
#         'oe.school.student.enrollment.file',
#         'doc_attachment_id', 'attachment_id',
#         'document_id',
#         string="Attachment")

class StudentEnrollmentAdmission(models.Model):
    _name = 'oe.school.student.enrollment.admission'
    _description = 'Gestion des Admission scolarité des étudiants'

    student_enrollemnt_id = fields.Many2one(
        'oe.school.student.enrollment', 
        string="Étudiant préinscrit", 
        # required=True,    
    )
    observations = fields.Html(string="Observations", required=True)

