# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class FeeslipRun(models.Model):
    _name = 'oe.feeslip.run'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Feeslip Batches'
    _order = 'date_end desc'

    name = fields.Char(required=True,)
    slip_ids = fields.One2many('oe.feeslip', 'feeslip_run_id', string='Feeslips', readonly=True,)
    state = fields.Selection([
        ('draft', 'New'),
        ('verify', 'Confirmed'),
        ('close', 'Done'),
        ('cancel', 'Cancel'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft', store=True, compute='_compute_state_change')
    date_start = fields.Date(string='Date From', required=True, 
        default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_end = fields.Date(string='Date To', required=True, 
        default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))

    fee_struct_id = fields.Many2one(
        'oe.fee.struct', string='Fee Structure',
        store=True, readonly=False, required=True,
    )
    
    feeslip_count = fields.Integer(compute='_compute_feeslip_count')
    company_id = fields.Many2one('res.company', string='Company', 
        default=lambda self: self.env.company)

    @api.onchange('fee_struct_id')
    def _onchange_fee_struct_id(self):
        today = datetime.today()
        first_day_of_month = today.replace(day=1)

        if self.fee_struct_id:
            self.date_start = first_day_of_month
            schedule_pay_duration = self.fee_struct_id.schedule_pay_duration
            date_to = first_day_of_month + relativedelta(months=schedule_pay_duration)
            self.date_end = date_to - relativedelta(days=1)  # To get the last day of the calculated month
        else:
            self.date_start = first_day_of_month
            last_day_of_month = first_day_of_month + relativedelta(months=1) - relativedelta(days=1)
            self.date_end = last_day_of_month
            
    def _compute_feeslip_count(self):
        for feeslip_run in self:
            feeslip_run.feeslip_count = len(feeslip_run.slip_ids)

    @api.depends('slip_ids', 'state')
    def _compute_state_change(self):
        for feeslip_run in self:
            if feeslip_run.state == 'draft' and feeslip_run.slip_ids:
                feeslip_run.update({'state': 'verify'})

    def action_draft(self):
        if self.slip_ids.filtered(lambda s: s.state == 'paid'):
            raise ValidationError(_('You cannot reset a batch to draft if some of the feeslips have already been confirmed.'))
        self.slip_ids.sudo().unlink()
        self.write({'state': 'draft'})
        self.slip_ids.write({'state': 'draft'})

    def action_cancel(self):
        if self.slip_ids.filtered(lambda s: s.state == 'paid'):
            raise ValidationError(_('You cannot cancel a batch if some of the feeslips have already been confirmed.'))
        self.slip_ids.sudo().action_feeslip_cancel()
        self.slip_ids.write({'state': 'cancel'})
        self.write({'state': 'cancel'})
        
    def action_open(self):
        self.write({'state': 'verify'})

    def action_close(self):
        if self._are_feeslips_ready():
            self.write({'state' : 'close'})

    def action_paid(self):
        self.mapped('slip_ids').action_feeslip_paid()
        self.write({'state': 'paid'})

    def action_validate(self):
        feeslip_done_result = self.mapped('slip_ids').filtered(lambda slip: slip.state not in ['draft', 'cancel']).action_feeslip_done()
        self.action_close()
        return feeslip_done_result

    def action_open_feeslips(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "oe.feeslip",
            "views": [[False, "tree"], [False, "form"]],
            "domain": [['id', 'in', self.slip_ids.ids]],
            "context": {'default_feeslip_run_id': self.id},
            "name": "Feeslips",
        }

    def action_open_feeslip_run_form(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'oe.feeslip.run',
            'views': [[False, 'form']],
            'res_id': self.id,
        }

    def _generate_feeslips(self):
        action = self.env["ir.actions.actions"]._for_xml_id("de_school_fees.action_feeslip_by_students")
        action['context'] = repr(self.env.context)
        return action

    @api.ondelete(at_uninstall=False)
    def _unlink_if_draft_or_cancel(self):
        if any(self.filtered(lambda feeslip_run: feeslip_run.state not in ('draft'))):
            raise UserError(_('You cannot delete a feeslip batch which is not draft!'))
        if any(self.mapped('slip_ids').filtered(lambda feeslip: feeslip.state not in ('draft', 'cancel'))):
            raise UserError(_('You cannot delete a feeslip which is not draft or cancelled!'))

    def _are_feeslips_ready(self):
        return all(slip.state in ['done', 'cancel'] for slip in self.mapped('slip_ids'))

    def action_feeslip_by_students(self):
        return {
            'name': 'Generate Feeslips',
            'view_mode': 'form',
            'res_model': 'oe.feeslip.students',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
