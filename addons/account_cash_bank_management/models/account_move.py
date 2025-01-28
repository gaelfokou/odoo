from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    transaction_date = fields.Date(
        string='Transaction Date',
        compute='_compute_transaction_date', store=True, readonly=False,
        index=True,
        precompute=True,
        copy=False,
    )

    @api.depends('statement_line_id')
    def _compute_transaction_date(self):
        for move in self:
            if move.statement_line_id:
                move.transaction_date = move.statement_line_id.date

    @api.depends('invoice_date', 'company_id', 'transaction_date')
    def _compute_date(self):
        res = super()._compute_date()
        for move in self:
            if not move.transaction_date:
                if not move.date:
                    move.date = fields.Date.context_today(self)
                continue
            move.date = move.transaction_date
        return res

