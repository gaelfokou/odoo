
from datetime import datetime, timedelta

from odoo import models, fields, api
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger("++++++++++++")

class FeeToCompleteFeePaymentWizard(models.TransientModel):
    _name = 'education.fee.payment.wizard'
    _description = 'modale pour compléter un paiement de scolarité'

    name = fields.Char('Réference du paiement', default='/')
    year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année académique',
        required=True
    )
    payment_id = fields.Many2one(
        'education.fee.payment',
        string='Paiement',
        required=True
    )
    student_id = fields.Many2one(
        'oe.school.student',
        string='Etudiant',
        related='payment_id.student_id',
        required=True
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
    amount_verse = fields.Monetary('Montant versé', required=True, related='payment_id.amount')
    amount_rest = fields.Monetary('Montant restant', required=True, related='payment_id.amount_rest')
    amount = fields.Monetary('Montant', required=True, tracking=True)
    reference = fields.Char('Réference du reçu', required=True, default='/')
    date_payment = fields.Date('Date de versement', required=True, default=fields.Date.context_today)
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        readonly=True,
        related_sudo=False
    )

    @api.model
    def default_get(self, fields):
        res = super(FeeToCompleteFeePaymentWizard, self).default_get(fields)
        if self.env.context.get('active_id'):
            res['payment_id'] = self.env.context.get('active_id')
            year_id = self.env['siantou.ems.core.year'].search(
                [('active', '=', True),],
                limit=1
            )
            payment_id = self.env['education.fee.payment'].search(
                [('id', '=',int(res['payment_id'])),],
                limit=1
            )
            if not year_id:
                raise ValidationError(f"Aucune année active trouvé")
            if not payment_id:
                raise ValidationError(f"Aucune paiement disponible pour {payment_id.student_id.name} pour l'année {year_id.name}")

            moratoire_id = self.env['siantou.ems.fee.moratoire'].search(
                [('student_id','=',payment_id.student_id.id)],
                limit=1
            )
            if moratoire_id:
                res['amount'] = moratoire_id.amount
            res['year_id'] = year_id.id

        return res

    def to_complete_student_fee_payment(self):
        if self.payment_id:
            _logger.info(f"Paiement In wizard ::: {self.payment_id.name}")

            if self.amount_rest>=self.amount:
                structure_frais_scol_id = self.payment_id.structure_frais_id
                journal_id = structure_frais_scol_id.type_frais_id.category_id.journal_id
                if not journal_id:
                    raise ValidationError("Le journal de paiement n'est pas configuré pour cette structure de frais")

                account_receivable_id = journal_id.default_account_id
                account_revenue_id = journal_id.default_account_id

                if not account_receivable_id or not account_revenue_id:
                    raise ValidationError("Les comptes de créance ou de revenus ne sont pas configurés dans le journal. Veuillez vérifier la configuration")

                lines = self.env['siantou.ems.fee.structure.lines'].sudo().search(
                    [('fee_structure_id','=',structure_frais_scol_id.id)],
                )
                tranches_remplit = []
                tranches_non_remplit = []
                pay_lines_incomplet = []
                amount_of_one_tranche = lines[0].fee_amount

                for line in self.payment_id.facture_ids:
                    tranches_remplit.append(line.structure_frais_line_id.id)

                ids_tranche_no_use = self.payment_id.get_liste_of_ids_tranche_no_use(
                    lines.ids,
                    tranches_remplit
                )

                for pay_line in self.payment_id.facture_ids:
                    if pay_line.amount_total<amount_of_one_tranche:
                        pay_lines_incomplet.append(pay_line)

                objs_tranche_no_use = []
                new_ids_tranche_no_use = []
                for id in ids_tranche_no_use:
                    line = lines.search([('id','=',id)], limit=1)
                    objs_tranche_no_use.append(line)
                    new_ids_tranche_no_use.append(line.id)

                amount_reste = 0
                if pay_lines_incomplet:
                    pay_line = pay_lines_incomplet[0]
                    if pay_line: 
                        amount_to_add = amount_of_one_tranche - pay_line.amount_total
                        amount_reste = self.amount - amount_to_add
                        if pay_line.amount_total<amount_of_one_tranche:
                            price_unit = 0
                            if amount_reste<=0:
                                if amount_reste==0:
                                    pay_line.update({
                                        'amount_total':pay_line.amount_total + self.amount,
                                        'pay_complet': True,
                                    })
                                if amount_reste<0:
                                    pay_line.update({
                                        'amount_total':pay_line.amount_total + self.amount,
                                        'pay_complet': False,
                                    })
                                price_unit = self.amount
                            if amount_reste>0:
                                pay_line.update({
                                    'amount_total':pay_line.amount_total + amount_to_add,
                                    'pay_complet': True,
                                })
                                price_unit = amount_to_add
                            account_move = self.payment_id.account_move(
                                self.student_id,
                                journal_id,
                                price_unit,
                                account_revenue_id
                            )
                else:
                    amount_reste = self.amount

                montant_total_remplit = 0
                if amount_reste>0:
                    nbre_tranches_a_remplir = (amount_reste)/amount_of_one_tranche
                    partie_entiere = int(nbre_tranches_a_remplir)
                    partie_decimal = round(nbre_tranches_a_remplir - partie_entiere, 2)
                    if partie_entiere>0:
                        tranches_remplit = []
                        # _logger.info(f"=== :: {objs_tranche_no_use}")
                        # _logger.info(f"==== :: {partie_entiere}")
                        for i in range(0, partie_entiere):
                            line = objs_tranche_no_use[i]
                            # _logger.info(line)
                            #=====vérification si la ligne de paiement existe déjà
                            price_unit = line.fee_amount
                            account_move = self.payment_id.account_move(
                                self.student_id, journal_id,
                                price_unit, account_revenue_id
                            )
                            self.env['siantou.ems.fee.payment.line'].create({
                                'invoice_id': account_move.id,
                                'payment_id': self.payment_id.id,
                                'structure_frais_line_id': line.id,
                                'amount_total': line.fee_amount,
                                'to_pay': True,
                                'pay_complet': True,
                                'mode_payment': self.mode_payment,
                                'cni': self.cni,
                                'lieu_delivr_cni': self.lieu_delivr_cni,
                                'date_delivr_cni': self.date_delivr_cni,
                                'titulaire_compte': self.titulaire_compte,
                                'name_bank': self.name_bank,
                                'code_guichet': self.code_guichet,
                                'numero_compte': self.numero_compte,
                                'date_payment': self.date_payment
                            })
                            montant_total_remplit+=line.fee_amount
                            tranches_remplit.append(line.id)

                    results = self.payment_id.get_liste_of_ids_tranche_no_use(new_ids_tranche_no_use, tranches_remplit)
                    if partie_decimal!=0.0:
                        #=== récupération de l'une des tranches qui n'est pas remplit
                        montant_total_remplit = amount_reste-montant_total_remplit
                        if results:
                            line_id = results[0]
                            price_unit = montant_total_remplit
                            account_move = self.payment_id.account_move(
                                self.student_id, journal_id,
                                price_unit, account_revenue_id
                            )
                            self.env['siantou.ems.fee.payment.line'].create({
                                'invoice_id': account_move.id,
                                'payment_id': self.payment_id.id,
                                'structure_frais_line_id': line_id,
                                'amount_total': montant_total_remplit,
                                'to_pay': True,
                                'pay_complet': False,
                                'mode_payment': self.mode_payment,
                                'cni': self.cni,
                                'lieu_delivr_cni': self.lieu_delivr_cni,
                                'date_delivr_cni': self.date_delivr_cni,
                                'titulaire_compte': self.titulaire_compte,
                                'name_bank': self.name_bank,
                                'code_guichet': self.code_guichet,
                                'numero_compte': self.numero_compte,
                                'date_payment': self.date_payment
                            })

                _logger.info(montant_total_remplit)

                amout_payment_total = sum([pay.amount_total for pay in self.payment_id.facture_ids])
                rest_diff = structure_frais_scol_id.amount_total-amout_payment_total
                if rest_diff==0:
                    self.payment_id.update({
                        'amount':amout_payment_total,
                        'amount_rest': 0.0,
                        'status': 'all'
                    })
                if rest_diff>0:
                    self.payment_id.update({
                        'amount':amout_payment_total,
                        'amount_rest': rest_diff,
                        'status': 'none_all'
                    })
            else:
                raise ValidationError(f"Le montant renseigné doit être inférieur ou égal à {self.amount_rest} (Montant qui reste à payer)")   

            return {'type': 'ir.actions.act_window_close'}

