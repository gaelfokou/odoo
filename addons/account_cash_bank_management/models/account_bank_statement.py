from markupsafe import Markup

from odoo import fields, models, api, _
import logging

from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AccountBankStatement (models.Model):
    _name = 'account.bank.statement'
    _inherit = ['account.bank.statement', 'mail.thread', 'mail.activity.mixin']

    state = fields.Selection([('open', 'Ouvert'), ('confirm', 'Fermé')], string='Status', required=True,
                             copy=False, default='open', readonly=True)
    move_line_count = fields.Integer(default=0)
    date = fields.Date(readonly=False)
    statement_line_count = fields.Integer(default=0, compute='_get_statement_line_count')
    move_line_ids = fields.One2many('account.move.line', 'statement_id', string='Entry lines')
    journal_type = fields.Selection(related='journal_id.type', help="Technical field used for usability purposes")
    all_lines_reconciled = fields.Boolean(compute='_check_lines_reconciled')

    journal_id = fields.Many2one(compute='_compute_journal_id2', readonly=False, precompute=True)

    @api.depends('line_ids.internal_index', 'line_ids.state')
    def _compute_date_index(self):
        for stmt in self:
            pass

    @api.depends('line_ids.journal_id')
    def _compute_journal_id2(self):
        for statement in self:
            pass

    def action_confirm(self):
        if not self.is_complete or not self.is_valid or any(not line.is_reconciled for line in self.line_ids):
            raise ValidationError(_("You cannot validate an invalid bank statement."))
        if self.filtered(lambda stmt: stmt.state != 'open'):
            raise ValidationError(_("You cannot validate this bank statement."))
        self.write({'state': 'confirm'})

    def action_draft(self):
        if self.filtered(lambda stmt: stmt.state != 'confirm'):
            raise ValidationError(_("You cannot set to new an this bank statement."))
        self.write({'state': 'open'})

    @api.depends('line_ids.journal_entry_ids')
    def _check_lines_reconciled(self):
        self.all_lines_reconciled = False
        # self.all_lines_reconciled = all([line.journal_entry_ids.ids or line.account_id.id for line in self.line_ids if not self.currency_id.is_zero(line.amount)])
        pass
    
    @api.depends()
    def _get_statement_line_count(self):
        for statement in self:
            statement.statement_line_count = len(statement.line_ids)

    @api.depends('move_line_ids')
    def _get_move_line_count(self):
        # for payment in self:
        #     payment.move_line_count = len(payment.move_line_ids)
        pass

    @api.model_create_multi
    def button_journal_entries(self):
        # context = dict(self._context or {})
        # context['journal_id'] = self.journal_id.id
        # return {
        #     'name': _('Journal Entries'),
        #     'view_type': 'form',
        #     'view_mode': 'tree,form',
        #     'res_model': 'account.move',
        #     'view_id': False,
        #     'type': 'ir.actions.act_window',
        #     'domain': [('id', 'in', self.mapped('move_line_ids').mapped('move_id').ids)],
        #     'context': context,
        # }
        pass

    @api.model_create_multi
    def check_confirm_bank(self):
        # if self.journal_type == 'cash' and not self.currency_id.is_zero(self.difference):
        #     action_rec = self.env['ir.model.data'].xmlid_to_object('account.action_view_account_bnk_stmt_check')
        #     if action_rec:
        #         action = action_rec.read([])[0]
        #         return action
        # return self.button_confirm_bank()
        pass

    @api.model
    def _action_open_bank_statements(self, extra_domain=None, default_context=None):
        context = default_context or {}
        views = [
            (self.env.ref('account_cash_bank_management.view_bank_statement_tree_custom').id, 'tree'),
            (self.env.ref('account_cash_bank_management.view_bank_statement_form_custom').id, 'form'),
        ]
        helper = Markup("<p class='o_view_nocontent_smiling_face'>{}</p><p>{}</p>").format(
            _("Nothing to do here!"),
            _("No transactions matching your filters were found."),
        )
        return {
            'name': _("Bank Statements"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement',
            'context': context,
            'view_mode': 'tree,form',
            'views': views,
            'help': helper,
        }

    def action_open_reconcile_statement(self):
        return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
            default_context={
                'search_default_statement_id': self.id,
            },
        )
