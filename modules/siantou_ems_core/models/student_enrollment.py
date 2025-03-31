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
        compute='_compute_registre',
        store=True
    )
    year_id = fields.Many2one(
        "siantou.ems.core.year", 
        string="Année académique", 
        default=lambda self: self.env['siantou.ems.core.year'].search([('active', '=', True)], limit=1)
    )
    name = fields.Char(
        string="Nom(s) et prénom(s)", 
        compute='_compute_name',
        store=True
    )

    matricule = fields.Char(string="Matricule")
    code_enrol = fields.Char(string="Code de préinscription", default="001485KOPLL")
    cycle_id = fields.Many2one(
        'oe.school.course',
        string='Cursus ou Cycle',
    )
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
    class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe',
        required=True
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
    date_naissance = fields.Date(string="Date de naissance")
    lieu_naissance = fields.Char(string="Lieu de naissance")
    sexe = fields.Selection([
        ('masculin', 'Masculin'),
        ('feminin', 'Féminin'),
    ], string="Sexe")
    situat_matri = fields.Selection([
        ('marie', 'Marié'),
        ('celibat', 'Célibataire'),
        ('concub', 'Concubinage'),
    ], string="Situation matrimoniale")
    nationalite = fields.Many2one(
        'siantou.ems.core.country',
        string="Nationalité(Pays d'origine)",
    )
    region_id = fields.Many2one("siantou.ems.core.region", string="Région")
    city_id = fields.Many2one("siantou.ems.core.city", string="Ville")
    quarter_id = fields.Many2one("siantou.ems.core.quarter", string="Quartier")

    autre = fields.Char(string="Autre pays")
    lieu_residence = fields.Char(string="Lieu de résidence")
    email = fields.Char(string="E-mail")
    num_tel = fields.Char(string="N° de Téléphone")
    diplo_requis_ids = fields.Many2many('oe.school.course.degree', string="Diplôme requis")
    session_lieu_obt = fields.Char(string="Session et lieu d'obtention")
    dern_etab_freq = fields.Char(string="Dernier établissement fréquenté")
    level_id = fields.Many2one("siantou.ems.core.level", string="Niveau", required=True)
    full_name_tutor = fields.Char(string="Nom(s) et prénom(s)")
    num_tel_tutor = fields.Char(string="N° de Téléphone")
    date_preins = fields.Datetime(string="Date de préinscription", default=datetime.datetime.now())
    status = fields.Selection([
            # ('broui', "En attente de paiement des frais d'inscription"),
            ('inscrip', 'Inscrit'),
            ('rej', 'Candidature rejeté'),
            ('transfer', 'Candidature accepté'),
        ],
        string="Status",
        default="inscrip",
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
        required=True
    )

    @api.depends('cycle_id')
    def _compute_registre(self):
        for record in self:
            registre_id = self.env['siantou.session.registre'].search([('cycle_id', '=', record.cycle_id.id)], limit=1)
            record.registre_id = registre_id

    @api.onchange('student_id')
    def _onchange_name(self):
        for record in self:
            record.name = record.student_id.name

    @api.depends('student_id')
    def _compute_name(self):
        for record in self:
            record.name = record.student_id.name

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

    def accepted_enrollment(self, student_enrol_id):
        if not student_enrol_id.status == "transfer":
            wizard = self.env['siantou.ems.core.student.enrollment.admission.wizard'].create({
                'student_enrollement_id': student_enrol_id.id,  # Pass the current student to the wizard
                'observations': 'Données de la candidature ok',  # Set the new state
            })
            wizard.create_creance(student_enrol_id)
            student_enrol_id.write({
                'status': 'transfer',
                'observations': 'Données de la candidature validées',
            })

    def rejected_enrollment(self, student_enrol_id):
        if not student_enrol_id.status == "rej":
            student_enrol_id.write({
                'status': 'rej',
                'observations': 'Données de la candidature rejetées',
            })
            account_move_id = self.env['account.move'].search([
                    ('partner_id','=',student_enrol_id.student_id.partner_id.id),
                    ('type_inclusion_fee','=','fee_inscrip'),
                    ('annee_academique_id','=',student_enrol_id.class_id.year_id.id),
                    ('level_id','=',student_enrol_id.class_id.level_id.id),
                    ('field_of_study_id','=',student_enrol_id.class_id.field_of_study_id.id),
                    ('cycle_id','=',student_enrol_id.class_id.field_of_study_id.cycle_id.id),
                ],
                limit=1
            )
            account_move_id.button_draft()
            account_move_id.unlink()

            account_move_ids = self.env['account.move'].search([
                    ('partner_id','=',student_enrol_id.student_id.partner_id.id),
                    ('type_inclusion_fee','=','fee_scol'),
                    ('annee_academique_id','=',student_enrol_id.class_id.year_id.id),
                    ('level_id','=',student_enrol_id.class_id.level_id.id),
                    ('field_of_study_id','=',student_enrol_id.class_id.field_of_study_id.id),
                    ('cycle_id','=',student_enrol_id.class_id.field_of_study_id.cycle_id.id),
                ]
            )
            for move_id in account_move_ids:
                move_id.button_draft()
                move_id.unlink()

    def action_accepted_enrollment(self):
        student_enrol_id = self.env['oe.school.student.enrollment'].search([
            ('id', '=', self.id),
        ], limit=1)
        if student_enrol_id:
            self.accepted_enrollment(student_enrol_id)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_rejected_enrollment(self):
        student_enrol_id = self.env['oe.school.student.enrollment'].search([
            ('id', '=', self.id),
        ], limit=1)
        if student_enrol_id:
            self.rejected_enrollment(student_enrol_id)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_all_accepted_enrollment(self):
        active_ids = self.env.context.get('active_ids', [])
        student_enrol_ids = self.env['oe.school.student.enrollment'].browse(active_ids)
        for student_enrol_id in student_enrol_ids:
            self.accepted_enrollment(student_enrol_id)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_all_rejected_enrollment(self):
        active_ids = self.env.context.get('active_ids', [])
        student_enrol_ids = self.env['oe.school.student.enrollment'].browse(active_ids)
        for student_enrol_id in student_enrol_ids:
            self.rejected_enrollment(student_enrol_id)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.model
    def unlink(self):
        if self.status == "transfer":
            raise ValidationError("Impossible de supprimer une candidature déjà admise")
        else:
            self.unlink()
        student_enrol = super(StudentEnrollment, self).unlink()
        return student_enrol

# class StudentEnrollmentFileAdmission(models.Model):
#     _name = 'oe.school.student.enrollment.file'
#     _description = "Gestion des fichiers d'enrollement des étudiants"

#     student_enrollemnt_id = fields.Many2one(
#         'oe.school.student.enrollment', 
#         string="Étudiant préinscrit", 
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
    )
    observations = fields.Html(string="Observations")

