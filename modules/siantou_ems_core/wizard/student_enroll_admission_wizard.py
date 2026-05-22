
from datetime import datetime
from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError

class StudentEnrollmentAdmissionWizard(models.TransientModel):
    _name = 'siantou.ems.core.student.enrollment.admission.wizard'
    _description = 'modale pour effectuer une admission'

    # student_id = fields.Many2one(
    #     'oe.school.student',
    #     string="Étudiant admis",
    #     # required=True,
    # )
    student_enroll_id = fields.Many2one(
        'oe.school.student.enrollment',
        string="Étudiant inscrit",
        # required=True,
    )

    observations = fields.Html(string="Observations", required=True)

    @api.model
    def default_get(self, fields):
        res = super(StudentEnrollmentAdmissionWizard, self).default_get(fields)
        # print(self.env.context.get('active_model'))
        if self.env.context.get('active_id'):
            res['student_enroll_id'] = self.env.context.get('active_id')
            _logger.info(f"Student admission ::: {res['student_enroll_id']}")
        return res

    def student_enroll_admission(self):
        student_id = None
        if self.student_enroll_id:
            self.student_enroll_id.student_id.write({
                'year_id': self.student_enroll_id.year_id.id,
                'school_id': self.student_enroll_id.school_id.id,
                'cycle_id': self.student_enroll_id.cycle_id.id,
                'field_of_study_id': self.student_enroll_id.field_of_study_id.id,
                'specialty_id': self.student_enroll_id.specialty_id.id,
                'option_id': self.student_enroll_id.option_id.id,
                'class_id': self.student_enroll_id.class_id.id,
                'type_cour': self.student_enroll_id.type_cour,
                'status_univ': self.student_enroll_id.status_univ,
                'level_id': self.student_enroll_id.level_id.id,
                'batch_id': self.student_enroll_id.batch_id.id,
            })
            self.student_enroll_id.write({
                'status': 'transfer',
                'observations': self.observations,
            })

            #=====Création d'un parcours étudiant
            # self.env['oe.school.student.career'].create({
            #     'student_id': student_id.id,
            #     'name': f"Admission DE {student_id.name}",
            #     'year_id': self.student_enroll_id.year_id.id,
            #     'level_id': self.student_enroll_id.level_id.id,
            #     'field_of_study_id': self.student_enroll_id.field_of_study_id.id,
            #     'cycle_id': self.student_enroll_id.cycle_id.id,
            #     'observations': self.observations,
            # })
            # _logger.info(self.student_enroll_id.cycle_id.name)

            year_id = self.env['siantou.ems.core.year'].search(
                [('is_active', '=', True),],
                limit=1
            )

            #=========================================================================================================
            #==============Création des frais rédevances d'inscription de la scolarité================================
            #=========================================================================================================
            """ structure_frais_inscript_id = self.env['siantou.ems.fee.structure'].sudo().search(
                [
                    ('field_of_study_ids','in',student_id.field_of_study_id.id),
                    ('level_id', '=', student_id.level_id.id),
                    ('type_paiement', '=', 'pu'),
                    ('type_inclusion_fee', '=', 'fee_inscrip'),
                    ('academic_year', '=', year_id.id),
                ],
                limit=1
            )
            _logger.info(student_id.field_of_study_id.name)
            _logger.info(student_id.level_id.name)
            _logger.info(year_id.name)
            if not structure_frais_inscript_id:
                raise ValidationError(f"Aucune structure de frais d'inscription disponible pour {self.student_enroll_id.field_of_study_id.name} {self.student_enroll_id.level_id.name} pour l'année {year_id.name}")

            journal_id = structure_frais_inscript_id.type_frais_id.category_id.journal_id
            if journal_id:
                account_receivable_id = journal_id.default_account_id
                account_revenue_id = journal_id.default_account_id
                if account_receivable_id or account_revenue_id:
                    _logger.info(structure_frais_inscript_id)
                    if structure_frais_inscript_id.type_inclusion_fee == 'fee_inscrip':
                            account_move_id = self.env['account.move'].search([
                                    ('partner_id', '=', self.student_enroll_id.partner_id.id),
                                    ('type_inclusion_fee', '=', 'fee_inscrip'),
                                    ('year_id', '=', structure_frais_inscript_id.academic_year.id),
                                    ('level_id', '=', self.student_enroll_id.level_id.id),
                                    ('field_of_study_id', '=', self.student_enroll_id.field_of_study_id.id),
                                    ('cycle_id', '=', self.student_enroll_id.field_of_study_id.cycle_id.id),
                                ],
                                limit=1
                            )
                            if not account_move_id:
                                mone_vals = {
                                    'move_type': 'out_invoice',
                                    'partner_id': self.student_enroll_id.partner_id.id,
                                    'journal_id': journal_id.id,
                                    'invoice_date': fields.Date.today(),
                                    'invoice_date_due': fields.Date.today(),
                                    'year_id': self.student_enroll_id.year_id.id,
                                    'level_id': self.student_enroll_id.level_id.id,
                                    'field_of_study_id': self.student_enroll_id.field_of_study_id.id,
                                    'cycle_id': self.student_enroll_id.field_of_study_id.cycle_id.id,
                                    'type_inclusion_fee':structure_frais_inscript_id.type_inclusion_fee,
                                    'ecole_id': self.student_enroll_id.field_of_study_id.school_id.id,
                                    'specialite_id': self.student_enroll_id.specialty_id.id,
                                    'ref': f"Frais {structure_frais_inscript_id.type_frais_id.name} de {self.student_enroll_id.name}",
                                    'invoice_line_ids':[
                                        (0,0,{
                                            'name': f"Frais {structure_frais_inscript_id.type_frais_id.name} de {self.student_enroll_id.name}",
                                            'quantity': 1.0,
                                            'price_unit': structure_frais_inscript_id.amount_total,
                                            'account_id': account_revenue_id.id,
                                        })
                                    ]
                                }
                                account_move_id = self.env['account.move'].create(mone_vals)
                                account_move_id.action_post() """

            #=========================================================================================================
            #==============Création des lignes de rédevance de la scolarité===========================================
            #=========================================================================================================
            """ structure_frais_id = self.env['siantou.ems.fee.structure'].sudo().search(
                [
                    ('field_of_study_ids','in',student_id.field_of_study_id.id),
                    ('level_id', '=', student_id.level_id.id),
                    ('type_paiement', '=', 'pt'),
                    ('type_inclusion_fee', '=', 'fee_scol'),
                    ('academic_year', '=', year_id.id),
                ],
                limit=1
            )

            _logger.info(structure_frais_id)
            journal_id = structure_frais_id.type_frais_id.category_id.journal_id
            if journal_id:
                account_receivable_id = journal_id.default_account_id
                account_revenue_id = journal_id.default_account_id

                if account_receivable_id or account_revenue_id:
                    _logger.info(structure_frais_id)
                    if structure_frais_id.type_inclusion_fee == 'fee_scol':
                        account_move_ids = self.env['account.move'].search([
                                ('partner_id', '=', self.student_enroll_id.partner_id.id),
                                ('type_inclusion_fee', '=', 'fee_scol'),
                                ('year_id', '=', structure_frais_id.academic_year.id),
                                ('level_id', '=', self.student_enroll_id.level_id.id),
                                ('field_of_study_id', '=', self.student_enroll_id.field_of_study_id.id),
                                ('cycle_id', '=', self.student_enroll_id.field_of_study_id.cycle_id.id),
                            ]
                        )
                        if len(account_move_ids)!=len(structure_frais_id.fee_type_ids):
                            for fee_line in structure_frais_id.fee_type_ids:
                                mone_vals = {
                                    'move_type': 'out_invoice',
                                    'partner_id': self.student_enroll_id.partner_id.id,
                                    'journal_id': journal_id.id,
                                    'invoice_date': fields.Date.today(),
                                    'invoice_date_due': fields.Date.today(),
                                    'year_id': self.student_enroll_id.year_id.id,
                                    'level_id': self.student_enroll_id.level_id.id,
                                    'field_of_study_id': self.student_enroll_id.field_of_study_id.id,
                                    'cycle_id': self.student_enroll_id.field_of_study_id.cycle_id.id,
                                    'type_inclusion_fee':structure_frais_id.type_inclusion_fee,
                                    'ecole_id': self.student_enroll_id.field_of_study_id.school_id.id,
                                    'specialite_id': self.student_enroll_id.specialty_id.id,
                                    'ref': f"Frais de {fee_line.name} de {self.student_enroll_id.name}",
                                    'invoice_line_ids':[
                                        (0,0,{
                                            'name': f"Frais de {fee_line.name} de {self.student_enroll_id.name}",
                                            'quantity': 1.0,
                                            'price_unit': fee_line.fee_amount,
                                            'account_id': account_revenue_id.id,
                                        })
                                    ]
                                }
                                account_move_id = self.env['account.move'].create(mone_vals)
                                account_move_id.action_post() """

            #=========================================================================================================
            #==============Création des lignes de rédevance pour les autres frais s'il existe déjà ===================
            #=========================================================================================================
            """ structure_spec_frais_ids = self.env['siantou.ems.fee.structure'].sudo().search(
                [
                    ('field_of_study_ids','in',student_id.field_of_study_id.id),
                    ('level_id', '=', student_id.level_id.id),
                    ('type_paiement', '=', 'pu'),
                    ('type_inclusion_fee', '=', 'fee_spec'),
                    ('academic_year', '=', year_id.id),
                ]
            )
            for struct_spec_id in structure_spec_frais_ids:
                journal_id = struct_spec_id.type_frais_id.category_id.journal_id
                if journal_id:
                    account_receivable_id = journal_id.default_account_id
                    account_revenue_id = journal_id.default_account_id
                    if account_receivable_id or account_revenue_id:
                        _logger.info(struct_spec_id)  
                        if struct_spec_id.type_inclusion_fee == 'fee_spec':
                            account_move_id = self.env['account.move'].search([
                                    ('partner_id', '=', self.student_enroll_id.partner_id.id),
                                    ('type_inclusion_fee', '=', 'fee_spec'),
                                    ('year_id', '=', struct_spec_id.academic_year.id),
                                    ('level_id', '=', self.student_enroll_id.level_id.id),
                                    ('field_of_study_id', '=', self.student_enroll_id.field_of_study_id.id),
                                    ('cycle_id', '=', self.student_enroll_id.field_of_study_id.cycle_id.id),
                                ],
                                limit=1
                            )
                            if not account_move_id:
                                mone_vals = {
                                    'move_type': 'out_invoice',
                                    'partner_id': self.student_enroll_id.partner_id.id,
                                    'journal_id': journal_id.id,
                                    'invoice_date': fields.Date.today(),
                                    'invoice_date_due': fields.Date.today(),
                                    'year_id': self.student_enroll_id.year_id.id,
                                    'level_id': self.student_enroll_id.level_id.id,
                                    'field_of_study_id': self.student_enroll_id.field_of_study_id.id,
                                    'cycle_id': self.student_enroll_id.field_of_study_id.cycle_id.id,
                                    'type_inclusion_fee':struct_spec_id.type_inclusion_fee,
                                    'ecole_id': self.student_enroll_id.field_of_study_id.school_id.id,
                                    'specialite_id': self.student_enroll_id.specialty_id.id,
                                    'ref': f"Frais {struct_spec_id.type_frais_id.name} de {self.student_enroll_id.name}",
                                    'invoice_line_ids':[
                                        (0,0,{
                                            'name': f"Frais {struct_spec_id.type_frais_id.name} de {self.student_enroll_id.name}",
                                            'quantity': 1.0,
                                            'price_unit': struct_spec_id.amount_total,
                                            'account_id': account_revenue_id.id,
                                        })
                                    ]
                                }
                                account_move_id = self.env['account.move'].create(mone_vals)
                                account_move_id.action_post() """

        return {'type': 'ir.actions.act_window_close'}
