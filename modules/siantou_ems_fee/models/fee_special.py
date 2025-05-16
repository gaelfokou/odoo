from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from . import utils
from datetime import date
import logging
_logger = logging.getLogger("Logger ==========")

class FeeSpecial(models.Model):
    _name = 'siantou.ems.fee.special'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _get_default_acadmic_year(self):
        """Get the default acedemic year active"""
        year = self.env['siantou.ems.core.year'].search(
            [('active', '=', True)], limit=1)
        if not year:
            raise UserError("""Aucune annéé academique activé, vous ne pouvez pas effectuer la facturation""")
        return year.id

    name = fields.Char('Réference du paiement', default='/')
    student_id = fields.Many2one(
        'oe.school.student',
        string='Etudiant',
        required=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='partner',
        related='student_id.partner_id'
    )
    fee_structure_id = fields.Many2one(
        'siantou.ems.fee.structure',
        string='Structure de frais',
        required=True,
        tracking=True
    )
    structure_frais_request_domain = fields.Binary(default=0, store=False)
    facture_id = fields.Many2one('account.move', string='Facture')
    amount = fields.Monetary(
        'Montant total',
        required=True,
        tracking=True,
        # store=False
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        readonly=True,
        related_sudo=False
    )
    mode_payment = fields.Selection(
        [
            ('bank', 'Virement bancaire'),
            ('cash', 'Paiement en espèce(Cash)')
        ],
        string='Mode de paiement',
        required=True,
        default="cash"
    )
    cni = fields.Char(string="Numéro CNI", required=True)
    date_delivr_cni = fields.Date(
        string="Date de délivrance",
        required=True
    )
    lieu_delivr_cni = fields.Char(
        string="Lieu de délivrance",
        required=True
    )
    titulaire_compte = fields.Char(string="Titulaire du compte")
    numero_compte = fields.Char(string="N° de compte")
    name_bank = fields.Char(string="Nom bank",)
    code_guichet = fields.Char(string="Code guichet")
    state = fields.Selection([
            ('no_create', "Encours de création"),
            ('create', 'Crée et attente de validation'),
            ('validate', 'Validé'),
        ], string='Statut',
        default='no_create',
        tracking=True
    )
    academic_year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année Académique',
        help="Séletionner l'Année Académique",
        required=True,
        default=lambda self: self._get_default_acadmic_year()
    )
    description = fields.Text('Description')
    date_payment = fields.Date(string="Date de paiement", default=fields.Date.context_today)

    @api.constrains('amount')
    def _constrains_amount(self):
        """Amount paid less or egal than amount of selected invoice"""
        for rec in self:
            if rec.amount <= 0:
                raise UserError("""Le montant du frais spécial ne peut être égal à 0""")

    @api.onchange('student_id')
    def _onchange_student_id(self):
        for rec in self:
            rec.structure_frais_request_domain = [
                ('level_id','=',rec.student_id.level_id.id),
                ('field_of_study_ids','in',rec.student_id.field_of_study_id.id),
                ('academic_year','=',rec.academic_year_id.id),
                ('type_inclusion_fee','=', 'fee_spec'),
                ('state','=', 'validate'),
            ]

    @api.onchange('fee_structure_id')
    def _onchange_fee_structure_id(self):
        for rec in self:
            rec.amount = rec.fee_structure_id.amount_total

    def validate_special(self):
        """Validate, create and match payment and invoice"""
        for rec in self:
            journal_id = rec.fee_structure_id.type_frais_id.category_id.journal_id
            if not journal_id:
                raise ValidationError("Le journal de paiement n'est pas configuré pour cette structure de frais")

            account_receivable_id = journal_id.default_account_id
            account_revenue_id = journal_id.default_account_id
            # _logger.info(account_receivable_id)
            # _logger.info(account_revenue_id)

            if not account_receivable_id or not account_revenue_id:
                raise ValidationError("Les comptes de créance ou de revenus ne sont pas configurés dans le journal. Veuillez vérifier la configuration")

            amount = 0
            if rec.fee_structure_id.type_paiement=='pu':
                amount = rec.fee_structure_id.amount_total
            _logger.info(amount)

            mone_vals = {
                'move_type': 'out_invoice',
                'partner_id': rec.student_id.partner_id.id,
                'journal_id': journal_id.id,
                'invoice_date': fields.Date.today(),
                'invoice_date_due': fields.Date.today(),
                'ref': f"Frais {rec.fee_structure_id.type_frais_id.name} de {rec.student_id.name}",
                'invoice_line_ids':[
                    (0,0,{
                        'name': f"Frais {rec.fee_structure_id.type_frais_id.name} de {rec.student_id.name}",
                        'quantity': 1.0,
                        'price_unit': amount,
                        'account_id': account_revenue_id.id,
                    })
                ]
            }
            move = self.env['account.move'].create(mone_vals)
            rec.facture_id = move.id
            rec.state = 'validate'

    def reset_special(self):
        """Cancel payment"""
        for rec in self:
            rec.facture_id.unlink()
            rec.state = 'create'
            # rec.unlink()

    def print_payement_special(self):
        for rec in self:
            factures = []
            amount_total = 0
            for line in rec:
                amount_total += line.amount
                factures.append({
                    'name':f"Frais {rec.fee_structure_id.type_frais_id.name}",
                    'amount_total':line.amount,
                    'date_payment':line.date_payment,
                    'currency_id':line.currency_id.name,
                })
            data = {
                'model':rec,
                'payment_id':{
                    'name':rec.name,
                    'year':rec.academic_year_id.name,
                },
                'student':{
                    'name':rec.student_id.name,
                    'matricule':rec.student_id.matricule,
                    'level':rec.student_id.level_id.name,
                    'field_of_study':rec.student_id.field_of_study_id.name,
                },
                'factures':factures,
                'date': fields.date.today(),
                'amount_total': amount_total,
            }

            _logger.info(data)
            #=====>>>>> Appeler le rapport PDF
            report_action = self.env.ref('siantou_ems_fee.action_report_student_fees_pdf')
            return report_action.report_action(self,data=data)

    @api.model
    def create(self, vals):
        """Over riding the create method to assign
        sequence for the newly creating the record"""
        vals['name'] = self.env['ir.sequence'].next_by_code(
            'siantou.ems.fee.special')
        student_id = self.env['oe.school.student'].search(
            [('id','=',vals['student_id'])],
            limit=1
        )
        structure_frais_id = self.env['siantou.ems.fee.structure'].search(
            [('id','=',vals['fee_structure_id'])],
            limit=1
        )
        pay_fee = self.env['siantou.ems.fee.special'].sudo().search([
                ('fee_structure_id','=',structure_frais_id.id),
                ('student_id','=',student_id.id),
                ('academic_year_id','=',vals['academic_year_id']),
            ],
            limit=1
        )
        if pay_fee:
            raise ValidationError(f"Un paiement de Mr/Mdme {student_id.name} existe déjà")

        res = super(FeeSpecial, self).create(vals)
        res.update({
            'state':'create'
        })
        return res

