from datetime import date, datetime

from odoo import fields, models, api


class AccountBankStatementLine (models.Model):
    _inherit = 'account.bank.statement.line'

    journal_entry_ids = fields.One2many('account.move.line', 'statement_line_id', 'Journal Items', copy=False,
                                        readonly=True)
    bank_account_id = fields.Many2one('res.partner.bank', string='Bank Account')
    date = fields.Date(related='statement_id.date', readonly=False)

    @api.model
    def create(self, vals):
        if 'statement_id' in vals:
            statement = self.env['account.bank.statement'].browse(vals.get('statement_id'))
            vals['date'] = statement.date
            return super(AccountBankStatementLine, self).create(vals)
        else:
            if vals.get('date'):
                _date = vals.get('date')
            elif self.date:
                _date = self.date
            else:
                _date = datetime.now()
            statement = self.env['account.bank.statement'].search([
                ('journal_id', '=', vals.get('journal_id')),
                ('date', '=', _date)
            ], limit=1)

        if not statement:
            statement = self.env['account.bank.statement'].create({
                'journal_id': vals.get('journal_id'),
                'date': _date,
                'state': 'open',
            })

        vals['statement_id'] = statement.id
        vals['date'] = statement.date

        return super(AccountBankStatementLine, self).create(vals)

    @api.depends('date', 'sequence')
    def _compute_internal_index(self):
        for rec in self:
            if not rec.date:
                rec.date = rec.statement_id.date
        return super()._compute_internal_index()

