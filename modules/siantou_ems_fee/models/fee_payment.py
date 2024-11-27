# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from . import utils
# from odoo.addons.siantou_ems_fee.models.utils import create_payment
import logging


_logger = logging.getLogger("+++++++++++++++++++++")


class FeePaymentLine(models.Model):
    _name = 'siantou.ems.fee.payment.line'


    invoice_id = fields.Many2one(
        'account.move', string='Facture', required=True)

    fee_structure = fields.Many2one(
        'siantou.ems.fee.structure', string="Libellé", related='invoice_id.fee_structure')

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

    name = fields.Char('Reference', default='/')

    student_id = fields.Many2one(
        'oe.school.student', string='Etudiant', required=True)

    # journal_id = fields.Many2one('account.journal',
    #                              domain=[('type', 'in', ('bank', 'cash'))],
    #                              string='Banque de paiement')
    structure_frais_id = fields.Many2one(
        'siantou.ems.fee.structure',
        string='Structure de frais',
        domain=[('is_scolarite', '=', True)],
    )
    amount = fields.Monetary('Montant versé', required=True, tracking=True)

    reference = fields.Char('Réference du reçu', required=True)

    date_payment = fields.Date('Date de versement', required=True)

    facture_ids = fields.One2many('siantou.ems.fee.payment.line',
                                  'payment_id', string='Liste des factures')

    currency_id = fields.Many2one(
        'res.currency', 
        default=lambda self: self.env.company.currency_id, 
        readonly=True, 
        related_sudo=False
    )
    # campus = fields.Many2one(
    #     'siantou.ems.core.campus',
    #     'Campus', 
    # )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Valider')
    ], string='Etat', default='draft', tracking=True)

    # @api.constrains('amount')
    # def _constrains_amount(self):
    #     """Amount paid less or egal than amount of selected invoice"""
    #     for rec in self:
    #         amount_fac = sum([x.amount_reste for x in rec.facture_ids])
    #         if amount_fac < rec.amount:
    #             raise UserError(""" Le montant des factures selectionnées est inférieur au montant versé,
    #                             Veuillez selectionner d'autres factures ou modifier le montant de versement
    #                             """)

    def validate_payment(self):
        """Validate, create and match payment and invoice"""
        payment_obj = self.env['account.payment']
        man_in = self.env.ref("account.account_payment_method_manual_in")
        t_pay = "inbound"
        p_met = man_in.id
        for rec in self:
            factures = sorted(rec.facture_ids, key=lambda r: r.sequence)
            montant = rec.amount
            for facture in factures:
                if(montant > 0 and facture.amount_reste > 0):
                    pay_amount = 0
                    if montant > facture.amount_reste:
                        pay_amount = facture.amount_reste
                        montant -= facture.amount_reste
                    elif montant <= facture.amount_reste:
                        pay_amount = montant
                        montant = 0
                    if facture.invoice_id.state=='draft':
                        facture.invoice_id.action_post()
                    active_ids = facture.invoice_id.ids
                    payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
                        'amount': pay_amount,
                        'journal_id':  self.env['account.journal'].search([
                                        ('type', 'in', ('bank', 'cash'))], limit=1).id,
                        'payment_date': rec.date_payment,
                    })._create_payments()
                    _logger.info(facture)
            rec.state = 'done'

    def reset_payment(self):
        """Cancel payment"""

        for rec in self:
            rec.state = 'draft'

    @api.onchange('student_id')
    def _onchange_student_id(self):
        """Show invoice of selected student"""
        for rec in self:
            for line in rec.facture_ids:
                line.sudo().unlink()
            if rec.id and len(rec.facture_ids) == 0:
                fees = self.env['account.move'].search(
                    [('move_type', '=', 'out_invoice'),('partner_id', '=', 
                    rec.student_enroll_id.partner_id.id.id),
                    ('academic_year_id', '=', rec.field_of_study_id.academic_year_id.id)])
                for fee in fees:
                    self.env['siantou.ems.fee.payment.line'].create({
                        'invoice_id': fee.id,
                        'payment_id': rec.id
                    })

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code(
            'education.fees.payment')
        res = super(FeePayment, self).create(vals)
        # if res.student_id.state == 'draft':
        #     res.student_id.create_fees()
        #     res._onchange_student_id()
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