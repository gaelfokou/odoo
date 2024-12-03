# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from . import utils
# from odoo.addons.siantou_ems_fee.models.utils import create_payment
import logging



_logger = logging.getLogger("+++++++++++++++++++++")


class FeePaymentLine(models.Model):
    _name = 'siantou.ems.fee.payment.line'


    invoice_id = fields.Many2one(
        'account.move', string='Facture', required=True)

    fee_structure = fields.Many2one(
        'siantou.ems.fee.structure', string="Libellé")

    sequence = fields.Integer('Séquence', related="fee_structure.sequence")

    amount_total = fields.Monetary(
        'Montant total', related='invoice_id.amount_total')

    amount_reste = fields.Monetary(
        'Montant restant', related='invoice_id.amount_residual')

    to_pay = fields.Boolean('A payer', default=False)

    payment_id = fields.Many2one('education.fee.payment', string='Paiement')

    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id, readonly=True)


class FeePayment(models.Model):
    _name = 'education.fee.payment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _sql_constraints = [
        ('unique_reference', 'unique_reference)', 'Cette reference existe déjà'),
    ]

    name = fields.Char('Reference', default='/')
    student_id = fields.Many2one('oe.school.student', string='Etudiant', required=True)
    structure_frais_id = fields.Many2one(
        'siantou.ems.fee.structure',
        string='Structure de frais',
        domain=[('type_inclusion_fee', '=', 'fee_scol')],
    )
    structure_frais_line_id = fields.Many2one(
        'siantou.ems.fee.structure.lines',
        string='Lignes de structure de frais',
        domain=[('id', '=',False)],
    )
    structure_frais_request_domain = fields.Binary(default=0, store=False)
    structure_frais_line_request_domain = fields.Binary(default=0, store=False)
    amount = fields.Monetary('Montant versé', required=True, tracking=True)
    reference = fields.Char('Réference du reçu', required=True)
    date_payment = fields.Date('Date de versement', required=True)
    facture_ids = fields.One2many(
        'siantou.ems.fee.payment.line',
        'payment_id', 
        string='Liste des factures'
    )
    currency_id = fields.Many2one(
        'res.currency', 
        default=lambda self: self.env.company.currency_id, 
        readonly=True, 
        related_sudo=False
    )
    year_id = fields.Many2one(
        'siantou.ems.core.year', 
        string='Année académique', 
        required=True,
        default=lambda self: self.env['siantou.ems.core.year'].search([('active','=',True)], limit=1),    
    )
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Valider')
    ], string='Etat', default='draft', tracking=True)


    @api.onchange('structure_frais_id')
    @api.depends('structure_frais_request_domain', 'structure_frais_line_request_domain')
    def _onchange_structure_frais_id(self):
        for rec in self:
            line_ids = self.env['siantou.ems.fee.structure.lines'].search([
                ('fee_structure_id', '=', rec.structure_frais_id.id),
            ])
            _logger.info(line_ids)

            if rec.structure_frais_id.type_paiement=='pt':
                rec.amount = False
                rec.structure_frais_line_request_domain= [('id', 'in', line_ids.ids)]
            if rec.structure_frais_id.type_paiement=='pu':
                rec.structure_frais_line_id = False
                self.amount = self.structure_frais_id.amount_total
                rec.structure_frais_line_request_domain= [('id', '=', False)]


    @api.onchange('structure_frais_line_id')
    def _onchange_structure_frais_line_id(self):
        structure_frais_line_id = self.env['siantou.ems.fee.structure.lines'].search([
                ('id', '=', self.structure_frais_line_id.id),
            ], limit=1
        )
        self.amount = structure_frais_line_id.fee_amount

    
    def validate_payment(self):
        """Validate, create and match payment and invoice"""

        for rec in self:
            journal_id = rec.structure_frais_id.type_frais_id.category_id.journal_id

            if not journal_id:
                raise ValidationError("Le journal de paiement n'est pas configuré pour cette structure de frais")
            
            account_receivable_id = journal_id.default_account_id
            account_revenue_id = journal_id.default_account_id
            _logger.info(account_receivable_id)
            _logger.info(account_revenue_id)

            if not account_receivable_id or not account_revenue_id:
                raise ValidationError("Les comptes de créance ou de revenus ne sont pas configurés dans le journal. Veuillez vérifier la configuration")
            amount = 0
            _logger.info(rec.structure_frais_id.type_paiement)
            if rec.structure_frais_id.type_paiement=='pt':
                amount = rec.structure_frais_line_id.fee_amount
            if rec.structure_frais_id.type_paiement=='pu':
                amount = rec.structure_frais_id.amount_total
            _logger.info(amount)

            mone_vals = {
                'move_type': 'out_invoice',
                'partner_id': rec.student_id.student_enroll_id.partner_id.id,
                'journal_id': journal_id.id,
                'invoice_date': fields.Date.today(),
                'invoice_date_due': fields.Date.today(),
                'ref': f"SCOLARITÉ de {rec.student_id.name}",
                'invoice_line_ids':[
                    (0,0,{
                        'name': f"Frais de scolarité de {rec.student_id.name}",
                        'quantity': 1.0,
                        'price_unit': amount,
                        'account_id': account_revenue_id.id,
                    })
                ]
            }
            self.env['account.move'].create(mone_vals)
            rec.state = 'done'


    def reset_payment(self):
        """Cancel payment"""
        for rec in self:
            rec.state = 'draft'


    @api.onchange('student_id')
    def _onchange_student_id(self):
        year_id = self.env['siantou.ems.core.year'].search([
            ('active','=',True)
        ], limit=1)
        for rec in self:
            rec.structure_frais_request_domain = [
                ('level_id','=',rec.student_id.level_id.id),
                ('field_of_study_id','=',rec.student_id.field_of_study_id.id),
                ('academic_year','=',year_id.id),
                ('type_inclusion_fee', '=', 'fee_scol')
            ]

        # for rec in self:
        #     structure_frais_id = self.env['siantou.ems.fee.structure'].search([
        #             ('level_id','=',rec.student_id.level_id.id),
        #             ('field_of_study_id','=',rec.student_id.field_of_study_id.id),
        #             ('academic_year','=',year_id.id),
        #         ], 
        #         limit=1
        #     )
        #     self.structure_frais_id = structure_frais_id.id
        #     for line in rec.facture_ids:
        #         line.sudo().unlink()
        #     if rec.id and len(rec.facture_ids) == 0:
        #         fees = self.env['account.move'].search(
        #             [('move_type', '=', 'out_invoice'),('partner_id', '=', 
        #             rec.student_enroll_id.partner_id.id.id),
        #             ('academic_year_id', '=', rec.field_of_study_id.academic_year_id.id)])
        #         for fee in fees:
        #             self.env['siantou.ems.fee.payment.line'].create({
        #                 'invoice_id': fee.id,
        #                 'payment_id': rec.id
        #             })


    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code(
            'education.fees.payment')
        #=== vérifier si un paiement de ce genre est déjà passé
        pay_frais_id = self.env['education.fee.payment'].search([
                ('structure_frais_id','=',int(vals['structure_frais_id'])),
                ('year_id','=',int(vals['year_id'])),
            ], limit=1
        )

        _logger.info(pay_frais_id)
        _logger.info(pay_frais_id.structure_frais_id.type_paiement)
        if pay_frais_id.structure_frais_id.type_paiement=="pt":
            pay_line_id = self.env['education.fee.payment'].search([
                    ('structure_frais_id','=',vals['structure_frais_id']),
                    ('year_id','=',int(vals['year_id'])),
                    ('structure_frais_line_id','=',vals['structure_frais_line_id']),
                ], limit=1
            )
            _logger.info(pay_frais_id.structure_frais_line_id)
            _logger.info(pay_line_id.id)
            _logger.info(int(vals['structure_frais_line_id']))
            if pay_line_id.id:
                raise ValidationError(f"Ce paiement a déjà été éffectué en {pay_line_id.year_id.name}")

        if pay_frais_id.structure_frais_id.type_paiement=="pu":
            raise ValidationError(f"Ce paiement a déjà été éffectué")

        res = super(FeePayment, self).create(vals)
        return res



class FeePaymentEnrollment(models.Model):
    _name = 'education.fee.payment.enrollment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Reference', default='/')

    student_id = fields.Many2one(
        'oe.school.student.enrollment', 
        string='Etudiant', required=True
    )
    structure_frais_id = fields.Many2one(
        'siantou.ems.fee.structure',
        string='Structure de frais'
    )
    amount = fields.Monetary('Montant versé', required=True, tracking=True)
    reference = fields.Char('Réference du reçu', required=True)
    date_payment = fields.Date('Date de versement', required=True)

    currency_id = fields.Many2one(
        'res.currency', 
        default=lambda self: self.env.company.currency_id, 
        readonly=True, 
        related_sudo=False
    )




