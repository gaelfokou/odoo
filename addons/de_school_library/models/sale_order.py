# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from math import ceil

from odoo import _, api, fields, models
from odoo.osv import expression
from odoo.tools import float_compare

class CirculationAgreement(models.Model):
    _inherit = 'sale.order'

    is_borrow_order = fields.Boolean("Circulation Agreement")
    borrow_status = fields.Selection([
        ('draft', 'Draft'),
        ('confirm','Confirm'), 
        ('reserve','Reserve'), # Reserve book will hold the book and will not avaible for issuance.
        ('issue','Issued'), # book issue to petron.
        ('return', 'Returned'), # book return by petron.
        ('done', 'Done'), # agreement closed 
        ('cancel', 'Cancelled'), 
    ], string="Borrow Status", default='draft', store=True, tracking=True, index=True,copy=False)

    borrow_next_action_date = fields.Datetime(
        string="Next Action", compute='_compute_next_action_date', store=True)

    is_book_late = fields.Boolean(
        string="Is overdue",
        help="The products haven't been picked-up or returned in time",
        compute='_compute_is_late',
    )
    
    #has_pickable_lines = fields.Boolean(compute="_compute_rental_status", store=True)
    #has_late_lines = fields.Boolean(compute="_compute_has_late_lines")

    # ============================================
    # ============= compute Methods ==============
    # ============================================
    @api.depends('is_borrow_order', 'borrow_next_action_date', 'borrow_status')
    def _compute_is_late(self):
        now = fields.Datetime.now()
        for order in self:
            tolerance_delay = relativedelta(hours=1)
            order.is_book_late = (
                order.is_borrow_order
                and order.borrow_status in ['issue', 'return']  # has_pickable_lines or has_returnable_lines
                and order.borrow_next_action_date
                and order.borrow_next_action_date + tolerance_delay < now
            )
            
    @api.depends(
        'state', 
        'order_line', 
        'order_line.product_uom_qty', 
        'order_line.qty_delivered', 
        'order_line.book_returned'
    )
    def _compute_next_action_date(self):
        for order in self:
            if order.state in ['sale', 'done'] and order.is_borrow_order:
                rental_order_lines = order.order_line.filtered(lambda l: l.is_borrow_order and l.book_issue_date and l.book_return_date)
                pickeable_lines = rental_order_lines.filtered(lambda sol: sol.qty_delivered < sol.product_uom_qty)
                returnable_lines = rental_order_lines.filtered(lambda sol: sol.book_returned < sol.qty_delivered)
                min_issue_date = min(pickeable_lines.mapped('book_issue_date')) if pickeable_lines else 0
                min_return_date = min(returnable_lines.mapped('book_return_date')) if returnable_lines else 0
                if min_issue_date and pickeable_lines and (not returnable_lines or min_issue_date <= min_return_date):
                    #order.borrow_status = 'issue'
                    order.borrow_next_action_date = min_issue_date
                elif returnable_lines:
                    #order.borrow_status = 'return'
                    order.borrow_next_action_date = min_return_date
                else:
                    #order.borrow_status = 'return'
                    order.borrow_next_action_date = False
                #order.has_pickable_lines = bool(pickeable_lines)
                #order.has_returnable_lines = bool(returnable_lines)
            else:
                #order.has_pickable_lines = False
                #order.has_returnable_lines = False
                #order.rental_status = order.state if order.is_borrow_order else False
                order.borrow_next_action_date = False
    
    @api.depends('is_borrow_order', 'borrow_next_action_date', 'borrow_status')
    def _compute_has_late_lines(self):
        for order in self:
            order.has_late_lines = (
                order.is_borrow_order
                and order.rental_status in ['pickup', 'return']  # has_pickable_lines or has_returnable_lines
                and order.borrow_next_action_date and order.borrow_next_action_date < fields.Datetime.now())


    def action_confirm(self):
        if self.is_borrow_order:
            self._action_borrow_order()
        else:
            super(CirculationAgreement, self).action_confirm()

    def _action_borrow_order(self):
        self.write({
            'state': 'sale',
            'borrow_status': 'confirm',
        })
    def open_issue_form(self):
        status = "confirm"
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        order_line_ids = self.order_line.filtered(
            lambda r: r.state in ['sale', 'done'] and r.is_borrow_order and float_compare(r.product_uom_qty, r.qty_delivered, precision_digits=precision) > 0)
        
        context = {
            'active_model': 'sale.order',
            'active_id': self.id,
            
            'order_line_ids': order_line_ids,
            'status': 'issue',
            'default_status': status,
            'default_order_id': self.id,
        }
        return {
            'name': _('Validate a issue') if status == 'confirm' else _('Validate a return'),
            'view_mode': 'form',
            'res_model': 'oe.library.process.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }
    def open_return_form(self):
        status = "issue"
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        order_line_ids = self.order_line.filtered(
            lambda r: r.state in ['sale', 'done'] and r.is_borrow_order and float_compare(r.product_uom_qty, r.qty_delivered, precision_digits=precision) > 0)
        
        context = {
            'active_model': 'sale.order',
            'active_id': self.id,
            'order_line_ids': order_line_ids,
            'status': 'return',
            'default_status': status,
            'default_order_id': self.id,
        }
        return {
            'name': _('Validate a issue') if status == 'confirm' else _('Validate a return'),
            'view_mode': 'form',
            'res_model': 'oe.library.process.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }