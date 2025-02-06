from odoo import fields, models, api, _
from odoo.tools.misc import clean_context
from odoo.exceptions import UserError


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    def _default_employee_id(self):
        employee_id = self.env['hr.employee'].search([], order='id asc', limit=1).id
        if not employee_id:
            raise UserError(_("Vous devez au moins créer un employé pour utiliser cette fonctionnalité"))
        return employee_id

    def _default_journal_id(self):
        journal_id = self.env['account.journal'].search([('type', '=', 'cash')], order='id asc', limit=1).id
        if not journal_id:
            raise UserError(_("Vous devez au moins créer un journal de caisse pour utiliser cette fonctionnalité"))
        return journal_id

    def _default_payment_method_line_id(self):
        journal_id = self.env['account.payment.method.line'].search([('journal_id.type', '=', 'cash')], order='id asc', limit=1).id
        if not journal_id:
            raise UserError(_("Vous devez au moins créer un journal de caisse pour utiliser cette fonctionnalité"))
        return journal_id

    ecole_id = fields.Many2one('siantou.ems.core.school', string='École')
    departement_id = fields.Many2one('hr.department', string='Département')
    filiere_id = fields.Many2one('siantou.ems.core.field_of_study', string='Filière')
    specialite_id = fields.Many2one('siantou.ems.core.specialty', string='Spécialité')
    annee_academique_id = fields.Many2one('siantou.ems.core.year', string='Année académique')
    cycle_id = fields.Many2one('oe.school.course', string='Cycle')
    employee_id = fields.Many2one(default=_default_employee_id)
    payment_mode = fields.Selection(default='company_account')
    employee_journal_id = fields.Many2one('account.journal', default=_default_journal_id)
    payment_method_line_id = fields.Many2one('account.payment.method.line', default=_default_payment_method_line_id)
    validation_cptble_ok = fields.Boolean('Validation comptable', copy=False, default=False)
    type_depense = fields.Selection([('academique', 'Académique'), ('maintenance', 'Maintenance')], string="Type de dépense")

    def action_refuse_expense_sheets(self):
        self.write({'validation_cptble_ok': False})
        return super().action_refuse_expense_sheets()

    def action_reset_approval_expense_sheets(self):
        self.write({'validation_cptble_ok': False})
        return super().action_refuse_expense_sheets()

    def action_open_acc_moves(self):
        res_model = 'account.move'
        record_ids = self.account_move_ids

        action = {'type': 'ir.actions.act_window', 'res_model': res_model}
        if len(self.account_move_ids) == 1:
            action.update({
                'name': record_ids.name,
                'view_mode': 'form',
                'res_id': record_ids.id,
                'views': [(False, 'form')],
            })
        else:
            action.update({
                'name': _("Journal entries"),
                'view_mode': 'list',
                'domain': [('id', 'in', record_ids.ids)],
                'views': [(False, 'list'), (False, 'form')],
            })
        return action

    def action_sheet_move_create_and_post(self):
        self._check_can_create_move()
        self._check_validation_cptable()
        self._do_create_and_post_moves()

    def _check_validation_cptable(self):
        for rec in self:
            if not rec.validation_cptble_ok:
                raise UserError(_("Vous ne pouvez pas décaisser sans avoir la validation du comptable"))

    def action_approbation_comptable(self):
        if self.filtered(lambda depense: depense.state != 'approve'):
            raise UserError(_("Vous ne pouvez pas effectuer d'approbation comptable pour une dépense qui n'est pas approuvée"))
        self._action_approbation_comptable()

    def _action_approbation_comptable(self):
        self.write({'validation_cptble_ok': True})


    def _do_create_and_post_moves(self):
        self = self.with_context(clean_context(self.env.context))  # remove default_*
        skip_context = {
            'skip_invoice_sync': True,
            'skip_invoice_line_sync': True,
            'skip_account_move_synchronization': True,
        }
        own_account_sheets = self.filtered(lambda sheet: sheet.payment_mode == 'own_account')
        company_account_sheets = self - own_account_sheets

        moves = self.env['account.move'].create([sheet._prepare_bills_vals() for sheet in own_account_sheets])
        # Set the main attachment on the moves directly to avoid recomputing the
        # `register_as_main_attachment` on the moves which triggers the OCR again
        for move in moves:
            move.message_main_attachment_id = move.attachment_ids[0] if move.attachment_ids else None
        for expense in company_account_sheets.expense_line_ids:
            transaction = self.env['account.bank.statement.line'].create(expense._prepare_transaction_vals())
            debit_move_line = transaction.move_id.line_ids[1]
            debit_move_line.write({'account_id': expense.account_id.id, 'name': expense.name})
            transaction.move_id.button_draft()
            moves |= transaction.move_id
        moves.action_post()
        self.activity_update()

        return moves


