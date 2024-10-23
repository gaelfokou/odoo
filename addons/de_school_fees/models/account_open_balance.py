# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FeeOpenBalanceLine(models.Model):
    _name = 'oe.feeslip.account.move.slip.line'
    _description = 'Open Balance Line'
    _order = 'id'

    name = fields.Char(compute='_compute_name', store=True, string='Description', readonly=False)
    feeslip_id = fields.Many2one('oe.feeslip', string='Fee Slip', ondelete='cascade', index=True)
    sequence = fields.Integer(required=True, index=True, default=10)
    amount_total = fields.Monetary(string='Total', readonly=True)
    amount_total_signed = fields.Monetary(string='Total Signed', readonly=True)
    amount_residual = fields.Monetary(string='Amount Due', readonly=True)
    amount_residual_signed = fields.Monetary(string='Amount Due Signed', readonly=True)
    currency_id = fields.Many2one('res.currency', related='feeslip_id.currency_id')

    #@api.depends('work_entry_type_id')
    def _compute_name(self):
        for record in self:
            record.name = record.name