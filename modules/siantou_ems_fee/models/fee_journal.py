# -*- coding: utf-8 -*-


from odoo import models, fields, api, _


class InheritJournal(models.Model):
    _inherit = 'account.journal'

    is_fee = fields.Boolean('Pour le paiement des frais ?', default=False)


    def action_create_new_fee(self):
        view = self.env.ref('siantou_ems_fee.receipt_form')
        ctx = self._context.copy()
        ctx.update({'journal_id': self.id, 'default_journal_id': self.id})
        ctx.update({'default_move_type': 'out_invoice'})

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'view_id': view.id,
            'context': ctx,
        }






