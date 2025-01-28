from markupsafe import Markup

from odoo import models, api, _, fields


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def open_action(self):
        res = super().open_action()
        if self.type in ('bank', 'cash') and not self._context.get('action_name'):
            self.ensure_one()
            return self.env['account.bank.statement']._action_open_bank_statements(
                extra_domain = [],
                default_context={
                    'default_journal_id': self.id,
                    # 'default_journal_trick_id': self.id,
                    'default_date': fields.Date.today(),
                    'search_default_journal_id': self.id,
                },
            )
        return res
