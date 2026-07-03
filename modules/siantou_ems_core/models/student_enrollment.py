# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP
from datetime import date, datetime, timedelta, time
import re
import psycopg2
import logging

_logger = logging.getLogger(__name__)

class StudentEnrollment(models.Model):
    _name = 'oe.school.student.enrollment'
    _description = 'Inscriptions des étudiants'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    name = fields.Char(
        string="Nom(s) et prénom(s)", 
        related='student_id.name',
        store=False
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
    batch_id = fields.Many2one(
        'siantou.ems.core.student.batch',
        string='Lot de l\'étudiant',
    )

    school_id = fields.Many2one(
        'siantou.ems.core.school',
        string='École',
        required=True
    )

    cycle_id = fields.Many2one(
        'oe.school.course',
        string='Cursus ou Cycle',
        required=True
    )

    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        string='Filière',
        related='specialty_id.field_of_study_id',
        store=False
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
        ], string='Type de cours',
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
    date_preins = fields.Datetime(string="Date de préinscription", default=datetime.now())
    status = fields.Selection([
            ('inscrip', 'Inscrit'),
            ('rej', 'Candidature rejeté'),
            ('transfer', 'Candidature accepté'),
        ], string='Statut',
        default='inscrip',
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

    priority = fields.Selection([
            ('1', 'Priorité 1'),
            ('2', 'Priorité 2'),
        ], 
        string="Priorité",
        default="1",
    )

    is_active_candidature = fields.Boolean(default=False, string="Activé")

    specialty_id_domain = fields.Binary(compute='_compute_school_domain', default=[])

    @api.depends('school_id', 'cycle_id')
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

    level_id_domain = fields.Binary(compute='_compute_level_domain', default=[])

    @api.depends('cycle_id')
    def _compute_level_domain(self):
        for record in self:
            domain = []
            if record.cycle_id.id:
                domain.append(('id', 'in', record.cycle_id.level_ids.ids))
            record.level_id_domain = domain

    @api.onchange('school_id')
    def _onchange_school(self):
        for record in self:
            record.cycle_id = None
            record.level_id = None
            record.class_id = None
            record.specialty_id = None
            record.option_id = None

    @api.onchange('cycle_id')
    def _onchange_cycle(self):
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

    def print_payement_student(self):
        for record in self:
            payment_id = self.env['education.fee.payment.enrollment'].search(
                [
                    ('student_id', '=', record.id),
                    ('year_id', '=', record.year_id.id),
                ], 
                limit=1
            )
            data = {
                # 'ids':record.ids,
                'model':record,
                'payment_id':{
                    'name':payment_id.name,
                    'year':payment_id.year_id.name,
                    'year':payment_id.year_id.name,
                },
                'student':{
                    'name':record.name,
                    'code_enrol':record.code_enrol,
                    'level':record.level_id.name,
                    'field_of_study':record.field_of_study_id.name,
                },
                'date': fields.date.today(),
                'facture': {
                    'name':f"INSCRIPTION {record.field_of_study_id.name} {record.level_id.name}",
                    'amount':payment_id.amount,
                    'date_payment':payment_id.date_payment,
                    'currency_id':payment_id.currency_id.name,
                },
            }

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
            'context': {
                'student_enroll_id': self.id,
            },
        })
        return action

    def accepted_enrollment(self, student_enroll_id):
        if not student_enroll_id.status == "transfer":
            wizard = self.env['siantou.ems.core.student.enrollment.admission.wizard'].create({
                'student_enroll_id': student_enroll_id.id,  # Pass the current student to the wizard
                'observations': 'Données de la candidature ok',  # Set the new state
            })
            wizard.create_creance(student_enroll_id)
            student_enroll_id.student_id.write({
                'year_id': student_enroll_id.year_id.id,
                'school_id': student_enroll_id.school_id.id,
                'cycle_id': student_enroll_id.cycle_id.id,
                'field_of_study_id': student_enroll_id.field_of_study_id.id,
                'specialty_id': student_enroll_id.specialty_id.id,
                'option_id': student_enroll_id.option_id.id,
                'class_id': student_enroll_id.class_id.id,
                'type_cour': student_enroll_id.type_cour,
                'status_univ': student_enroll_id.status_univ,
                'level_id': student_enroll_id.level_id.id,
                'batch_id': student_enroll_id.batch_id.id,
            })
            student_enroll_id.write({
                'status': 'transfer',
                'observations': 'Données de la candidature validées',
            })

    def rejected_enrollment(self, student_enroll_id):
        if not student_enroll_id.status == "rej":
            student_enroll_id.write({
                'status': 'rej',
                'observations': 'Données de la candidature rejetées',
            })
            account_move_id = self.env['account.move'].search([
                    ('partner_id', '=', student_enroll_id.student_id.partner_id.id),
                    ('type_inclusion_fee', '=', 'fee_inscrip'),
                    ('year_id', '=', student_enroll_id.class_id.year_id.id),
                    ('level_id', '=', student_enroll_id.class_id.level_id.id),
                    ('field_of_study_id', '=', student_enroll_id.class_id.field_of_study_id.id),
                    ('cycle_id', '=', student_enroll_id.class_id.field_of_study_id.cycle_id.id),
                ],
                limit=1
            )
            account_move_id.button_draft()
            account_move_id.unlink()

            account_move_ids = self.env['account.move'].search([
                    ('partner_id', '=', student_enroll_id.student_id.partner_id.id),
                    ('type_inclusion_fee', '=', 'fee_scol'),
                    ('year_id', '=', student_enroll_id.class_id.year_id.id),
                    ('level_id', '=', student_enroll_id.class_id.level_id.id),
                    ('field_of_study_id', '=', student_enroll_id.class_id.field_of_study_id.id),
                    ('cycle_id', '=', student_enroll_id.class_id.field_of_study_id.cycle_id.id),
                ]
            )
            for move_id in account_move_ids:
                move_id.button_draft()
                move_id.unlink()

    def action_accepted_enrollment(self):
        student_enroll_id = self.env['oe.school.student.enrollment'].search([
            ('id', '=', self.id),
        ], limit=1)
        if student_enroll_id:
            self.accepted_enrollment(student_enroll_id)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_rejected_enrollment(self):
        student_enroll_id = self.env['oe.school.student.enrollment'].search([
            ('id', '=', self.id),
        ], limit=1)
        if student_enroll_id:
            self.rejected_enrollment(student_enroll_id)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_all_accepted_enrollment(self):
        active_ids = self.env.context.get('active_ids', [])
        student_enroll_ids = self.env['oe.school.student.enrollment'].browse(active_ids)
        student_enroll_ids = list(student_enroll_ids)
        for student_enroll_id in student_enroll_ids:
            self.accepted_enrollment(student_enroll_id)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_all_rejected_enrollment(self):
        active_ids = self.env.context.get('active_ids', [])
        student_enroll_ids = self.env['oe.school.student.enrollment'].browse(active_ids)
        student_enroll_ids = list(student_enroll_ids)
        for student_enroll_id in student_enroll_ids:
            self.rejected_enrollment(student_enroll_id)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.model
    def create(self, vals):
        if 'class_id' not in vals:
            class_id = None
        else:
            class_id = self.env['siantou.ems.core.class'].browse(vals['class_id'])

        specialty_id = self.env['siantou.ems.core.specialty'].browse(vals['specialty_id'])
        vals['school_id'] = specialty_id.field_of_study_id.school_id.id
        vals['field_of_study_id'] = specialty_id.field_of_study_id.id

        if not class_id:
            class_id = self.env['siantou.ems.core.class'].search([
                ('specialty_id', '=', vals['specialty_id']),
                ('option_id', '=', vals['option_id']),
                ('level_id', '=', vals['level_id']),
                ('year_id', '=', vals['year_id']),
                ('type_cour', '=', vals['type_cour']),
            ], limit=1)
            if not class_id:
                raise UserError('Aucune classe trouvée')
                # class_id = self.env['siantou.ems.core.class'].create({
                #     'school_id': vals['school_id'],
                #     'field_of_study_id': vals['field_of_study_id'],
                #     'specialty_id': vals['specialty_id'],
                #     'option_id': vals['option_id'],
                #     'level_id': vals['level_id'],
                #     'year_id': vals['year_id'],
                #     'type_cour': vals['type_cour'],
                # })
        vals['class_id'] = class_id.id

        if 'batch_id' not in vals:
            batch_id = self.env['siantou.ems.core.student.batch'].assign_batch(
                class_id.id
            )
            vals['batch_id'] = batch_id.id

        cycle_id = self.env['oe.school.course'].browse(vals['cycle_id'])
        if not cycle_id:
            field_of_study_id = self.env['siantou.ems.core.field_of_study'].browse(vals['field_of_study_id'])
            if field_of_study_id:
                cycle_id = field_of_study_id.cycle_id
                vals['cycle_id'] = cycle_id.id

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

        res = super(StudentEnrollment, self).create(vals)

        if 'class_id' in vals:
            classe = self.env['siantou.ems.core.class'].search([
                ('id', '=', vals['class_id']),
            ], limit=1)
            if classe:
                classe._compute_students()
                classe._compute_number_of_students()
                classe.sudo().write({
                    'number_of_student': classe.number_of_student,
                })

        return res

    def write(self, vals):
        student_enrolls = []
        if len(self.ids) == 1:
            student_enroll = self.env['oe.school.student.enrollment'].browse(self.id)
            student_enrolls.append(student_enroll)
        else:
            student_enrolls = self.env['oe.school.student.enrollment'].browse(self.ids)
            student_enrolls = list(student_enrolls)

        for student_enroll in student_enrolls:
            student_enroll = self.env['oe.school.student.enrollment'].browse(self.id)

            if 'class_id' not in vals:
                vals['class_id'] = student_enroll.class_id.id
            if 'school_id' not in vals:
                vals['school_id'] = student_enroll.school_id.id
            if 'field_of_study_id' not in vals:
                vals['field_of_study_id'] = student_enroll.field_of_study_id.id
            if 'specialty_id' not in vals:
                vals['specialty_id'] = student_enroll.specialty_id.id
            if 'option_id' not in vals:
                vals['option_id'] = student_enroll.option_id.id
            if 'level_id' not in vals:
                vals['level_id'] = student_enroll.level_id.id
            if 'year_id' not in vals:
                vals['year_id'] = student_enroll.year_id.id
            if 'type_cour' not in vals:
                vals['type_cour'] = student_enroll.type_cour if student_enroll.type_cour else 'cj'
            if 'cycle_id' not in vals:
                vals['cycle_id'] = student_enroll.cycle_id.id

            class_id = self.env['siantou.ems.core.class'].browse(vals['class_id'])

            if not class_id:
                class_id = self.env['siantou.ems.core.class'].search([
                    ('specialty_id', '=', vals['specialty_id']),
                    ('option_id', '=', vals['option_id']),
                    ('level_id', '=', vals['level_id']),
                    ('year_id', '=', vals['year_id']),
                    ('type_cour', '=', vals['type_cour']),
                ], limit=1)
                if not class_id:
                    raise UserError('Aucune classe trouvée')
                    # class_id = self.env['siantou.ems.core.class'].create({
                    #     'school_id': vals['school_id'],
                    #     'field_of_study_id': vals['field_of_study_id'],
                    #     'specialty_id': vals['specialty_id'],
                    #     'option_id': vals['option_id'],
                    #     'level_id': vals['level_id'],
                    #     'year_id': vals['year_id'],
                    #     'type_cour': vals['type_cour'],
                    # })
            vals['class_id'] = class_id.id

            if 'batch_id' not in vals:
                batch_id = self.env['siantou.ems.core.student.batch'].assign_batch(
                    class_id.id
                )
                vals['batch_id'] = batch_id.id

            cycle_id = self.env['oe.school.course'].browse(vals['cycle_id'])
            if not cycle_id:
                field_of_study_id = self.env['siantou.ems.core.field_of_study'].browse(vals['field_of_study_id'])
                if field_of_study_id:
                    cycle_id = field_of_study_id.cycle_id
                    vals['cycle_id'] = cycle_id.id

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

        res = super(StudentEnrollment, self).write(vals)

        if 'class_id' in vals:
            classe = self.env['siantou.ems.core.class'].search([
                ('id', '=', vals['class_id']),
            ], limit=1)
            if classe:
                classe._compute_students()
                classe._compute_number_of_students()
                classe.sudo().write({
                    'number_of_student': classe.number_of_student,
                })

        return res

    def unlink(self):
        student_enrols = []
        if len(self.ids) == 1:
            student_enrol = self.env['oe.school.student.enrollment'].browse(self.id)
            student_enrols.append(student_enrol)
        else:
            student_enrols = self.env['oe.school.student.enrollment'].browse(self.ids)
            student_enrols = list(student_enrols)

        class_id = None

        for student_enrol in student_enrols:
            if self.status == "transfer":
                raise ValidationError("Impossible de supprimer une candidature déjà admise")
            class_id = student_enrol.class_id if student_enrol.class_id.id else None

        student_enrol = super(StudentEnrollment, self).unlink()

        if class_id:
            classe = self.env['siantou.ems.core.class'].search([
                ('id', '=', class_id.id),
            ], limit=1)
            if classe:
                classe._compute_students()
                classe._compute_number_of_students()
                classe.sudo().write({
                    'number_of_student': classe.number_of_student,
                })

        return student_enrol

    def update_enrollment(self, student_enroll):
        try:
            if not student_enroll.class_id.id or not student_enroll.school_id.id or not student_enroll.cycle_id.id:
                student_enroll.write({
                    'year_id': student_enroll.student_id.year_id.id if student_enroll.student_id.year_id.id else student_enroll.year_id.id,
                    'school_id': student_enroll.student_id.school_id.id if student_enroll.student_id.school_id.id else student_enroll.school_id.id,
                    'cycle_id': student_enroll.student_id.cycle_id.id if student_enroll.student_id.cycle_id.id else student_enroll.cycle_id.id,
                    'field_of_study_id': student_enroll.student_id.field_of_study_id.id if student_enroll.student_id.field_of_study_id.id else student_enroll.field_of_study_id.id,
                    'specialty_id': student_enroll.student_id.specialty_id.id if student_enroll.student_id.specialty_id.id else student_enroll.specialty_id.id,
                    'option_id': student_enroll.student_id.option_id.id if student_enroll.student_id.option_id.id else student_enroll.option_id.id,
                    # 'class_id': student_enroll.student_id.class_id.id if student_enroll.student_id.class_id.id else student_enroll.class_id.id,
                    'type_cour': student_enroll.student_id.type_cour if student_enroll.student_id.type_cour else student_enroll.type_cour,
                    'status_univ': student_enroll.student_id.status_univ if student_enroll.student_id.status_univ else student_enroll.status_univ,
                    'level_id': student_enroll.student_id.level_id.id if student_enroll.student_id.level_id.id else student_enroll.level_id.id,
                    'batch_id': student_enroll.student_id.batch_id.id if student_enroll.student_id.batch_id.id else student_enroll.batch_id.id,
                })
            # self.env.cr.commit()
        except psycopg2.errors.NotNullViolation as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except psycopg2.Error as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except Exception as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

    def action_update_all_enrollment(self):
        active_ids = self.env.context.get('active_ids', [])
        student_enrolls = self.env['oe.school.student.enrollment'].browse(active_ids)
        student_enrolls = list(student_enrolls)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')

        for student_enroll in student_enrolls:
            self.update_enrollment(student_enroll)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

# class StudentEnrollmentFileAdmission(models.Model):
#     _name = 'oe.school.student.enrollment.file'
#     _description = 'Fichier d\'enrollement des étudiants'

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
    _description = 'Admission scolarité des étudiants'

    student_enrollemnt_id = fields.Many2one(
        'oe.school.student.enrollment', 
        string="Étudiant préinscrit", 
    )

    observations = fields.Html(string="Observations")

