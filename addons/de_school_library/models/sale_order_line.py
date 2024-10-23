# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta, date
from pytz import timezone, UTC

from odoo import api, fields, models, _
from odoo.tools import format_datetime, format_time
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    borrow_status = fields.Selection(related='order_id.borrow_status')
    is_borrow_order = fields.Boolean(related='order_id.is_borrow_order')
    is_product_book = fields.Boolean(related='product_id.is_book', depends=['product_id'])

    book_issue_date = fields.Datetime(string='Issue Date',
            default=lambda s: fields.Datetime.now() + relativedelta(minute=0, second=0, hours=1))
    book_return_date = fields.Datetime(string="Return Date",
            default=lambda s: fields.Datetime.now() + relativedelta(minute=0, second=0, hours=1, days=1))
    duration = fields.Integer(
        string="Duration", compute="_compute_book_duration",
        help="The duration unit is based on the unit of the rental pricing rule.")
    duration_unit = fields.Selection([("hour", "Hours"), ("day", "Days"), ("week", "Weeks"), ("month", "Months"), ('year', "Years")],
                                     string="Unit", required=True, compute="_compute_book_duration")

    book_pricing_id = fields.Many2one('oe.library.product.fees', compute="_compute_book_pricing",
        string="Pricing", help="Best Pricing Rule based on duration")

    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    book_returned = fields.Float("Returned", default=0.0, copy=False)

    is_book_late = fields.Boolean(
        string="Is overdue", compute='_compute_is_book_late',
        help="The products haven't been returned in time")

    library_issue_lot_ids = fields.Many2many('stock.lot', 'library_issue_lot_rel', domain="[('product_id','=',product_id)]", copy=False)
    library_returned_lot_ids = fields.Many2many('stock.lot', 'library_returned_lot_rel', domain="[('product_id','=',product_id)]", copy=False)
    
    @api.depends('book_return_date')
    def _compute_is_book_late(self):
        now = fields.Datetime.now()
        late = False
        for line in self:
            if line.book_return_date:
                if line.book_return_date < now:
                    late = True
            line.write({
                'is_book_late': late,
            })
                
            #line.is_book_late = False #line.book_return_date < now

    
    @api.depends('book_pricing_id', 'book_issue_date', 'book_return_date')
    def _compute_book_duration(self):
        for wizard in self:
            values = {
                'duration_unit': 'day',
                'duration': 1.0,
            }
            if wizard.book_issue_date and wizard.book_return_date:
                duration_dict = self.env['oe.library.product.fees']._compute_duration_vals(wizard.book_issue_date, wizard.book_return_date)
                if wizard.book_pricing_id:
                    values = {
                        'duration_unit': wizard.book_pricing_id.library_fee_period_id.unit,
                        'duration': duration_dict[wizard.book_pricing_id.library_fee_period_id.unit]
                    }
                else:
                    values = {
                        'duration_unit': 'day',
                        'duration': duration_dict['day']
                    }
            wizard.update(values)

    @api.depends('book_issue_date','book_return_date','is_borrow_order')
    def _compute_name(self):
        """Override to add the compute dependency.

        The custom name logic can be found below in _get_sale_order_line_multiline_description_sale.
        """
        super()._compute_name()
        
    def _get_sale_order_line_multiline_description_sale(self):
        """Add Rental information to the SaleOrderLine name."""
        res = super()._get_sale_order_line_multiline_description_sale()
        if self.is_borrow_order:
            self._compute_unit_price()
            res += self._get_book_order_line_description()
        return res

    def _get_book_order_line_description(self):
        tz = self._get_tz()
        if self.book_issue_date and self.book_return_date\
           and self.book_issue_date.replace(tzinfo=UTC).astimezone(timezone(tz)).date()\
               == self.book_return_date.replace(tzinfo=UTC).astimezone(timezone(tz)).date():
            # If return day is the same as pickup day, don't display return_date Y/M/D in description.
            return_date_part = format_time(self.with_context(use_babel=True).env, self.book_return_date, tz=tz, time_format=False)
        else:
            return_date_part = format_datetime(self.with_context(use_babel=True).env, self.book_return_date, tz=tz, dt_format=False)

        return "\n%s %s %s" % (
            format_datetime(self.with_context(use_babel=True).env, self.book_issue_date, tz=tz, dt_format=False),
            _("to"),
            return_date_part,
        )
        
    def _get_tz(self):
        return self.env.context.get('tz') or self.env.user.tz or 'UTC'
        
    @api.depends('book_issue_date', 'book_return_date','product_id','duration')
    def _compute_book_pricing(self):
        for wizard in self:
            if wizard.product_id:
                company = wizard.company_id or wizard.env.company
                wizard.book_pricing_id = test = wizard.product_id._get_best_library_fee_rule(
                    start_date=wizard.book_issue_date,
                    end_date=wizard.book_return_date,
                    pricelist=wizard.pricelist_id,
                    company=company,
                    currency=wizard.currency_id or company.currency_id,
                )

    @api.onchange('book_pricing_id', 'currency_id', 'duration', 'duration_unit')
    #@api.depends('book_pricing_id', 'currency_id', 'duration', 'duration_unit')
    def _compute_unit_price(self):
        for wizard in self:
            if wizard.is_product_book:
                if wizard.pricelist_id:
                    wizard.price_unit = wizard.pricelist_id._get_product_price(
                        wizard.product_id, 1, start_date=wizard.book_issue_date,
                        end_date=wizard.book_return_date
                    )
                    #raise UserError(wizard.pricelist_id._get_product_price(
                    #    wizard.product_id, 1, start_date=wizard.book_issue_date,
                    #    end_date=wizard.book_return_date
                    #))
                    
                elif wizard.book_pricing_id and wizard.duration > 0:
                    price_unit = wizard.book_pricing_id._compute_price(wizard.duration, wizard.duration_unit)
                    if wizard.currency_id != wizard.book_pricing_id.currency_id:
                        wizard.price_unit = wizard.book_pricing_id.currency_id._convert(
                            from_amount=price_unit,
                            to_currency=wizard.currency_id,
                            company=wizard.company_id,
                            date=fields.Date.today())
                    else:
                        wizard.price_unit = price_unit
                elif wizard.duration > 0:
                    wizard.price_unit = wizard.product_id.lst_price
    
                product_taxes = wizard.product_id.taxes_id.filtered(lambda tax: tax.company_id.id == wizard.company_id.id)
                if wizard.id:
                    product_taxes_after_fp = wizard.tax_id
                elif 'sale_order_line_tax_ids' in self.env.context:
                    product_taxes_after_fp = self.env['account.tax'].browse(self.env.context['sale_order_line_tax_ids'] or [])
                else:
                    product_taxes_after_fp = product_taxes
    
                # TODO : switch to _get_tax_included_unit_price() when it allow the usage of taxes_after_fpos instead
                # of fiscal position. We cannot currently use the fpos because JS only has access to the line information
                # when opening the wizard.
                product_price_unit = wizard.price_unit
                if set(product_taxes.ids) != set(product_taxes_after_fp.ids):
                    flattened_taxes_before_fp = product_taxes._origin.flatten_taxes_hierarchy()
                    if any(tax.price_include for tax in flattened_taxes_before_fp):
                        taxes_res = flattened_taxes_before_fp.compute_all(
                            product_price_unit,
                            quantity=wizard.quantity,
                            currency=wizard.currency_id,
                            product=wizard.product_id,
                        )
                        product_price_unit = taxes_res['total_excluded']
    
                    flattened_taxes_after_fp = product_taxes_after_fp._origin.flatten_taxes_hierarchy()
                    if any(tax.price_include for tax in flattened_taxes_after_fp):
                        taxes_res = flattened_taxes_after_fp.compute_all(
                            product_price_unit,
                            quantity=wizard.quantity,
                            currency=wizard.currency_id,
                            product=wizard.product_id,
                            handle_price_include=False,
                        )
                        for tax_res in taxes_res['taxes']:
                            tax = self.env['account.tax'].browse(tax_res['id'])
                            if tax.price_include:
                                product_price_unit += tax_res['amount']
                    wizard.price_unit = product_price_unit
        
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Clean rental related data if new product cannot be rented."""
        if (not self.is_product_book) and self.is_borrow_order:
            self.update({
                'is_borrow_order': False,
                'book_issue_date': False,
                'book_return_date': False,
            })
        #self.schedule_product()
       
    def _generate_delay_line(self, qty):
        """Generate a sale order line representing the delay cost due to the late return.

        :param float qty:
        :param timedelta duration:
        """
        self.ensure_one()

        self.order_id.update({
            'note': str(fields.Datetime.now()),
        })
        
        if qty <= 0 or not self.is_book_late:
            return

        duration = fields.Datetime.now() - self.return_date

        #delay_price = self.product_id._compute_delay_price(duration)
        #if delay_price <= 0.0:
        #    return

        
        # migrate to a function on res_company get_extra_product?
        delay_product = self.company_id.book_charge_product_id
        
        if not delay_product:
            delay_product = self.env['product.product'].with_context(active_test=False).search(
                [('default_code', '=', 'BOOK_Charge'), ('type', '=', 'service')], limit=1)
            if not delay_product:
                delay_product = self.env['product.product'].create({
                    "name": "Book Charge",
                    "standard_price": 0.0,
                    "type": 'service',
                    "default_code": "BOOK_Charge",
                    "purchase_ok": False,
                })
                # Not set to inactive to allow users to put it back in the settings
                # In case they removed it.
            self.company_id.book_charge_product_id = delay_product

        if not delay_product.active:
            return

        delay_price = self.product_id.currency_id._convert(
            from_amount=delay_price,
            to_currency=self.currency_id,
            company=self.company_id,
            date=date.today(),
        )

        vals = self._prepare_delay_line_vals(delay_product, delay_price, qty)

        self.order_id.write({
            'order_line': [(0, 0, vals)]
        })

    def schedule_product(self):
        action = self.env['ir.actions.actions']._for_xml_id('de_school_library.action_sale_order_line')
        context = {
            'active_model': 'sale.order.line',
            'active_ids': self.ids,
            'active_id': self.id,
        }
        action['context'] = context
        action['res_id'] = self.id
        return action