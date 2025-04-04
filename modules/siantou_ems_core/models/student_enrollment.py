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

    name = fields.Char(
        string="Nom(s) et prénom(s)", 
        related='student_id.name',
        store=True
    )
    registre_id = fields.Many2one(
        'siantou.session.registre', 
        "Registre d'admission" ,
        # domain="[('state', '=', 'application')]",
    )
    year_id = fields.Many2one(
        "siantou.ems.core.year", 
        string="Année académique", 
        default=lambda self: self.env['siantou.ems.core.year'].search([('is_active', '=', True)], limit=1)
    )
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
    diplo_requis_ids = fields.Many2many('oe.school.course.degree', string="Diplôme requis")
    session_lieu_obt = fields.Char(string="Session et lieu d'obtention")
    dern_etab_freq = fields.Char(string="Dernier établissement fréquenté")
    level_id = fields.Many2one("siantou.ems.core.level", string="Niveau", required=True)
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
                    ('year_id','=',student_enrol_id.class_id.year_id.id),
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
                    ('year_id','=',student_enrol_id.class_id.year_id.id),
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
    def create(self, vals):
        class_id = self.env['siantou.ems.core.class'].browse(vals['class_id'])
        if not class_id:
            class_id = self.env['siantou.ems.core.class'].search([
                ('field_of_study_id', '=', vals['field_of_study_id']),
                ('specialty_id', '=', vals['specialty_id']),
                ('option_id', '=', vals['option_id']),
                ('level_id', '=', vals['level_id']),
            ], limit=1)
            if not class_id:
                field_of_study_id = self.env['siantou.ems.core.field_of_study'].search([('id', '=', vals['field_of_study_id'])], limit=1)
                school_id = None
                if field_of_study_id:
                    school_id = field_of_study_id.school_id.id
                class_id = self.env['siantou.ems.core.class'].create({
                    'school_id': school_id,
                    'field_of_study_id': vals['field_of_study_id'],
                    'specialty_id': vals['specialty_id'],
                    'option_id': vals['option_id'],
                    'level_id': vals['level_id'],
                    'year_id': vals['year_id'],
                    'type_cour': vals['type_cour'],
                })
        vals['class_id'] = class_id.id

        student_id = self.env['oe.school.student'].browse(vals['student_id'])
        batch_id = student_id.batch_id
        if not batch_id.id:
            batch_id = self.env['siantou.ems.core.student.batch'].assign_batch(
                class_id.field_of_study_id.school_id.id,
                class_id.field_of_study_id.id,
                class_id.specialty_id.id,
                class_id.option_id.id,
                class_id.level_id.id
            )
        student_id.write({
            'year_id': vals['year_id'],
            'cycle_id': vals['cycle_id'],
            'field_of_study_id': vals['field_of_study_id'],
            'specialty_id': vals['specialty_id'],
            'option_id': vals['option_id'],
            'class_id': vals['class_id'],
            'type_cour': vals['type_cour'],
            'status_univ': vals['status_univ'],
            'level_id': vals['level_id'],
            'batch_id': batch_id.id,
        })

        cycle_id = self.env['oe.school.course'].browse(vals['cycle_id'])
        diplo_requis = self.env['oe.school.course.degree'].search([('cycle_ids', '=', vals['cycle_id'])])
        diplo_requis_ids = diplo_requis.ids
        if len(diplo_requis_ids) == 0:
            diplo_requis = cycle_id.diplo_requis_ids.create({
                'name': cycle_id.name,
            })
            diplo_requis_ids.append(diplo_requis.id)
        vals['diplo_requis_ids'] = diplo_requis_ids

        registre_id = self.env['siantou.session.registre'].search([('cycle_id', '=', vals['cycle_id'])], limit=1)
        if registre_id:
            vals['registre_id'] = registre_id.id

        student_enroll = super(StudentEnrollment, self).create(vals)

        return student_enroll

    # def write(self, vals):
    #     registre_id = self.env['siantou.session.registre'].search([('cycle_id', '=', vals['cycle_id'])], limit=1)
    #     if registre_id:
    #         vals['registre_id'] = registre_id.id

    #     student_enroll = super(StudentEnrollment, self).write(vals)

    #     return student_enroll

    def unlink(self):
        if self.status == "transfer":
            raise ValidationError("Impossible de supprimer une candidature déjà admise")

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

