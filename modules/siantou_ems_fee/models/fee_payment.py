# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from . import utils
# from odoo.addons.siantou_ems_fee.models.utils import create_payment
import logging

_logger = logging.getLogger("+++++++++++++++++++++")

class FeePaymentLine(models.Model):
    _name = 'siantou.ems.fee.payment.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    invoice_id = fields.Many2one(
        'account.move', string='Facture', required=True)
    payment_id = fields.Many2one(
        'education.fee.payment',
        string='Paiement',
        required=True,
        ondelete='cascade',
        index=True
    )
    structure_frais_line_id = fields.Many2one(
        'siantou.ems.fee.structure.lines',
        string='Lignes de structure de frais',
        required=True
        # domain=[('id', '=', False)],
    )
    mode_payment = fields.Selection(
        [
            ('bank', 'Virement bancaire'),
            ('cash', 'Paiement en espèce(Cash)')
        ],
        string='Mode de paiement',
        required=True
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
    # sequence = fields.Integer('Séquence', related="structure_frais_line_id.sequence")
    amount_total = fields.Monetary('Montant versé')
    # amount_reste = fields.Monetary('Montant à compléter')
    # amount_reste = fields.Monetary('Montant restant', related='invoice_id.amount_residual')
    to_pay = fields.Boolean('A payer', default=False)
    pay_complet = fields.Boolean('Paiement complèt', default=False)
    date_payment = fields.Date('Date de versement', required=True)
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        readonly=True
    )

class FeePayment(models.Model):
    _name = 'education.fee.payment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _sql_constraints = [
        ('unique_reference', 'unique_reference)', 'Cette reference existe déjà'),
    ]

    name = fields.Char('Réference', default='/')
    mode_payment = fields.Selection(
        [
            ('bank', 'Virement bancaire'),
            ('cash', 'Paiement en espèce(Cash)')
        ],
        string='Mode de paiement',
        required=True,
        default="cash"
    )
    student_id = fields.Many2one('oe.school.student', string='Etudiant', required=True)
    structure_frais_id = fields.Many2one(
        'siantou.ems.fee.structure',
        string='Structure de frais',
        domain=[('type_inclusion_fee', '=', 'fee_scol')],
        required=True
    )
    structure_frais_request_domain = fields.Binary(default=0, store=False)
    amount = fields.Monetary('Montant versé', required=True, tracking=True)
    amount_rest = fields.Monetary('Montant à compléter', default=0, required=True, tracking=True)
    reference = fields.Char('Réference du reçu')
    date_payment = fields.Date('Date de versement', required=True, default=fields.Date.context_today)
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
        default=lambda self: self.env['siantou.ems.core.year'].search([('active', '=', True)], limit=1),
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
            ('creer', 'Création'),
            ('draft', 'En attente de validation'),
            ('done', 'Validé')
        ],
        string='Etat',
        default='creer',
        tracking=True, required=True
    )
    status = fields.Selection([
            ('none', 'one'),
            ('all', 'Oui'),
            ('none_all', 'Non')
        ],
        default='none',
        string='Paiement complèt ?',
        tracking=True, required=True
    )
    use_moratoire = fields.Boolean("Utilisé un moratoire ?", default=False)

    def action_complete_fee_payment_wizard(self):
        action = self.env.ref('siantou_ems_fee.action_complete_fee_payment_wizard').read()[0]
        action.update({
            'name': f"Compléter le paiement ===> {self.name}",
            'res_model': 'education.fee.payment.wizard',
            'type': 'ir.actions.act_window',
        })
        return action

    def get_liste_of_ids_tranche_no_use(self, list_tranche_ids_of_structure, list_tranche_ids_use):
        results = []
        for id in list_tranche_ids_of_structure:
            if id not in list_tranche_ids_use:
                results.append(id)
        return results

    def validate_payment(self):
        """Validate, create and match payment and invoice"""

        for rec in self:
            journal_id = rec.structure_frais_id.type_frais_id.category_id.journal_id
            if not journal_id:
                raise ValidationError("Le journal de paiement n'est pas configuré pour cette structure de frais")

            account_receivable_id = journal_id.default_account_id
            account_revenue_id = journal_id.default_account_id
            if not account_receivable_id or not account_revenue_id:
                raise ValidationError("Les comptes de créance ou de revenus ne sont pas configurés dans le journal. Veuillez vérifier la configuration")

            price_unit = 0
            structure_frais_scol_id = rec.structure_frais_id

            # pay_fees = self.env['education.fee.payment'].sudo().search([
            #     ('id','!=',rec.id),
            #     ('structure_frais_id','=',structure_frais_scol_id.id),
            #     ('student_id','=',rec.student_id.id),
            #     ('year_id','=',rec.year_id.id),
            # ])
            # amount_pay = 0
            # for pay in pay_fees:
            #     amount_pay = amount_pay + sum([p_line.amount_total for p_line in pay.facture_ids])

            lines = self.env['siantou.ems.fee.structure.lines'].sudo().search(
                [('fee_structure_id','=',structure_frais_scol_id.id)],
            )
            # if amount_pay<structure_frais_scol_id.amount_total:
            #     if len(pay_fees)==0:

            rest_diff = structure_frais_scol_id.amount_total-rec.amount
            if rec.amount<=0:
                raise ValidationError("Le montant versé doit être supérieur à 0")

            if rest_diff<0:
                raise ValidationError(f"Le montant versé doit être inférieur ou égal à {structure_frais_scol_id.amount_total}")

            amount_of_one_tranche = lines[0].fee_amount
            nbre_tranches_a_remplir = (rec.amount)/amount_of_one_tranche
            partie_entiere = int(nbre_tranches_a_remplir)
            partie_decimal = round(nbre_tranches_a_remplir - partie_entiere, 2)

            _logger.info(partie_entiere)
            _logger.info(partie_decimal)

            # nbre_tranches_disp = len(lines)
            # diff_nbre_tranch = nbre_tranches_disp - int(nbre_tranches_a_remplir)

            tranches_remplit = []
            montant_total_remplit = 0
            if partie_entiere>0:
                for i in range(0, partie_entiere):
                    line = lines[i]
                    #=====vérification si la ligne de paiement existe déjà
                    price_unit = line.fee_amount
                    account_move = self.account_move(
                        rec.student_id, journal_id,
                        price_unit, account_revenue_id
                    )
                    self.env['siantou.ems.fee.payment.line'].create({
                        'invoice_id': account_move.id,
                        'payment_id': rec.id,
                        'structure_frais_line_id': line.id,
                        'amount_total': line.fee_amount,
                        'to_pay': True,
                        'pay_complet': True,
                        'mode_payment':rec.mode_payment,
                        'date_payment': rec.date_payment
                    })
                    montant_total_remplit+=line.fee_amount
                    tranches_remplit.append(line.id)

            results = self.get_liste_of_ids_tranche_no_use(lines.ids, tranches_remplit)
            if partie_decimal!=0.0:
                #=== récupération de l'une des tranches qui n'est pas remplit
                _amount = rec.amount-montant_total_remplit
                # amount_rest = (line.fee_amount)-_amount
                _logger.info(results)
                line_id = results[0]
                price_unit = _amount
                account_move = self.account_move(
                    rec.student_id, journal_id,
                    price_unit, account_revenue_id
                )
                self.env['siantou.ems.fee.payment.line'].create({
                    'invoice_id': account_move.id,
                    'payment_id': rec.id,
                    'structure_frais_line_id': line_id,
                    'amount_total': _amount,
                    'to_pay': True,
                    'pay_complet': False,
                    'mode_payment':rec.mode_payment,
                    'date_payment': rec.date_payment
                })

            #==== mise à jour du paiement actuelle

            if rest_diff==0:
                rec.update({
                    'amount_rest': 0.0,
                    'status': 'all'
                })
            if rest_diff>0:
                rec.update({
                    'amount_rest': rest_diff,
                    'status': 'none_all'
                })

            rec.state = 'done'

    def account_move(self, student_id, journal_id, price_unit, account_revenue_id):
        mone_vals = {
            'move_type': 'out_invoice',
            'partner_id': student_id.partner_id.id,
            'journal_id': journal_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_date_due': fields.Date.today(),
            'ref': f"SCOLARITÉ de {student_id.name}",
            'invoice_line_ids':[
                (0,0,{
                    'name': f"Frais de scolarité de {student_id.name}",
                    'quantity': 1.0,
                    'price_unit': price_unit,
                    'account_id': account_revenue_id.id,
                })
            ]
        }
        account_move = self.env['account.move'].create(mone_vals)
        return account_move

    def reset_payment(self):
        """Cancel payment"""
        for rec in self:
            rec.facture_ids.unlink()
            rec.amount = 0.0
            rec.amount_rest = 0.0
            rec.state = 'creer'
            rec.status = 'none'

    def action_rien(self):
        """Cancel payment"""
        for rec in self:
            pass

    def print_payement_student(self):
        for rec in self:
            factures = []
            amount_total = 0
            for line in rec.facture_ids:
                amount_total += line.amount_total
                factures.append({
                    'name':line.structure_frais_line_id.name,
                    'amount_total':line.amount_total,
                    'date_payment':line.date_payment,
                    'currency_id':line.currency_id.name,
                })
            data = {
                # 'ids':rec.ids,
                'model':rec,
                'payment_id':{
                    'name':rec.name,
                    'year':rec.year_id.name,
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

    @api.onchange('student_id')
    def _onchange_student_id(self):
        for rec in self:
            rec.structure_frais_request_domain = [
                ('level_id','=',rec.student_id.level_id.id),
                ('field_of_study_ids','in',rec.student_id.field_of_study_id.id),
                ('academic_year','=',rec.year_id.id),
                ('type_inclusion_fee','=', 'fee_scol'),
                ('state','=', 'validate'),
            ]
            moratoire_id = self.env['siantou.ems.fee.moratoire'].search(
                [('student_id','=',rec.student_id.id)],
                limit=1
            )
            if moratoire_id:
                rec.amount = moratoire_id.amount
                rec.use_moratoire = True
            else:
                rec.amount = 0
                rec.use_moratoire = False

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code(
            'education.fees.payment'
        )
        student_id = self.env['oe.school.student'].search(
            [('id','=',vals['student_id'])],
            limit=1
        )
        structure_frais_id = self.env['siantou.ems.fee.structure'].search(
            [('id','=',vals['structure_frais_id'])],
            limit=1
        )
        pay_fee = self.env['education.fee.payment'].sudo().search([
                ('structure_frais_id','=',structure_frais_id.id),
                ('student_id','=',student_id.id),
                ('year_id','=',vals['year_id']),
            ],
            limit=1
        )
        if pay_fee:
            raise ValidationError(f"Un paiement de Mr/Mdme {student_id.name} existe déjà")

        if vals['amount']<=0:
            raise ValidationError("Le montant versé doit être supérieur à 0")

        if structure_frais_id.amount_total<vals['amount']:
            raise ValidationError(f"Le montant versé doit être inférieur ou égal à {structure_frais_id.amount_total}")

        vals['state'] = 'draft'
        res = super(FeePayment, self).create(vals)
        return res

    @api.model
    def write(self, vals):
        res = super(FeePayment, self).write(vals)
        return res

class FeePaymentEnrollment(models.Model):
    _name = 'education.fee.payment.enrollment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Reference', default='/')

    student_enrol_id = fields.Many2one(
        'oe.school.student.enrollment',
        string='Candidature',
        required=True
    )
    student_id = fields.Many2one(
        'oe.school.student',
        string='Étudiant',
        related='student_enrol_id.student_id',
        store=True
    )
    student_name = fields.Char(
        string='Nom du déposant',
        related='student_id.name'
    )
    student_phone = fields.Char(
        string='Téléphone du déposant',
        related='student_id.num_tel'
    )
    structure_frais_id = fields.Many2one(
        'siantou.ems.fee.structure',
        string='Structure de frais'
    )
    year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année académique',
        required=True,
        default=lambda self: self.env['siantou.ems.core.year'].search([('active', '=', True)], limit=1),
    )
    amount = fields.Monetary('Montant versé', required=True, tracking=True)
    amount_plus = fields.Monetary('Montant en plus', default=0, required=True, tracking=True)
    amount_moins = fields.Monetary('Montant en moins', default=0, required=True, tracking=True)
    reference = fields.Char('Réference du reçu')
    date_payment = fields.Date('Date de versement', required=True)
    status = fields.Selection([
        ('all', 'Oui'),
        ('none_all', 'Non')
    ], string='Paiement complèt')
    mode_payment = fields.Selection(
        [
            ('bank', 'Virement bancaire'),
            ('cash', 'Paiement en espèce(Cash)')
        ],
        string='Mode de paiement',
        default="cash",
        required=True
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
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        readonly=True,
        related_sudo=False
    )

