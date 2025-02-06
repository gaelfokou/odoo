from odoo import fields, models, Command, api, _
from odoo.exceptions import UserError


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    def _default_product_id(self):
        product_id = self.env['product.product'].search([
            ('detailed_type', '=', 'service'),
            ('purchase_ok', '=', True),
            ('can_be_expensed', '=', True)], limit=1).id
        if not product_id:
            raise UserError(_("Vous devez au moins créer un service pouvant être inséré dans une note de frais \n"
                              "pour utiliser cette fonctionnalité"))
        return product_id

    ecole_id = fields.Many2one('siantou.ems.core.school', string='École')
    departement_id = fields.Many2one('hr.department', string='Département')
    filiere_id = fields.Many2one('siantou.ems.core.field_of_study', string='Filière')
    specialite_id = fields.Many2one('siantou.ems.core.specialty', string='Spécialité')
    annee_academique_id = fields.Many2one('siantou.ems.core.year', string='Année académique')
    cycle_id = fields.Many2one('oe.school.course', string='Cycle')
    payment_mode = fields.Selection(default='company_account')
    product_id = fields.Many2one('product.product', default=_default_product_id)

    def _prepare_transaction_vals(self):
        self.ensure_one()

        journal = self.sheet_id.journal_id
        payment_method_line = self.sheet_id.payment_method_line_id
        statement = self.env['account.bank.statement'].search([
            ('date', '=', self.date),
            ('create_uid', '=', self.env.user.id),
            ('state', '=', 'open'),
            ('journal_id', '=', journal.id)
        ], limit=1)
        if not statement:
            raise UserError(_("Vous devez ouvrir une caisse ou un brouillard de banque à la date du %s pour enregistrer le décaissement", self.date))
        if not payment_method_line:
            raise UserError(_("Vous avez manqué d'ajouter une méthode de paiement manuel au niveau du journal (%s)", journal.name))

        return {
            #**self.sheet_id._prepare_move_vals(),
            'date': self.date,  # Overidden from self.sheet_id._prepare_transaction_vals() so we can use the expense date for the account move date
            'payment_ref': self.name,
            'ref': self.name,
            'ecole_id': self.sheet_id.ecole_id.id,
            'departement_id': self.sheet_id.departement_id.id,
            'filiere_id': self.sheet_id.filiere_id.id,
            'specialite_id': self.sheet_id.specialite_id.id,
            'annee_academique_id': self.sheet_id.annee_academique_id.id,
            'cycle_id': self.sheet_id.cycle_id.id,
            'partner_id': False,
            'journal_id': journal.id,
            'expense_sheet_id': self.sheet_id.id,
            'statement_id': statement.id,
            'amount': self.total_amount_currency * (-1),
            'currency_id': self.currency_id.id,
            'attachment_ids': [
                Command.create(attachment.copy_data({'res_model': 'account.move', 'res_id': False, 'raw': attachment.raw})[0])
                for attachment in self.message_main_attachment_id]
        }



