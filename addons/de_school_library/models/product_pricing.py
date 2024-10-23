# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import math
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _, _lt
from odoo.exceptions import ValidationError
from odoo.tools import format_amount, float_compare, float_is_zero

# For our use case: pricing depending on the duration, the values should be sufficiently different from one plan to
# another to not suffer from the approcimation that all months are 31 longs.
# otherwise, 31 days would result in 2 month.
PERIOD_RATIO = {
    'hour': 1,
    'day': 24,
    'week': 24 * 7,
    'month': 24*31, # average number of days per month over the year
    'year': 24*31*12,
}


class ProductLibraryFees(models.Model):
    """ Library Fees """
    _name = 'oe.library.product.fees'
    _description = 'Library Pricing'
    _order = 'product_template_id,price,pricelist_id,library_fee_period_id'

    name = fields.Char(compute='_compute_name')
    description = fields.Char(compute='_compute_description')
    library_fee_period_id = fields.Many2one('oe.library.fees.period', string='Recurrency', required=True)
    price = fields.Monetary(string="Price", required=True, default=1.0)
    currency_id = fields.Many2one('res.currency', 'Currency', compute='_compute_currency_id', store=True)
    product_template_id = fields.Many2one('product.template', string="Product Templates", ondelete='cascade',
                                          help="Select products on which this pricing will be applied.")
    product_variant_ids = fields.Many2many('product.product', string="Product Variants",
                                           help="Select Variants of the Product for which this rule applies. Leave empty if this rule applies for any variant of this template.")
    pricelist_id = fields.Many2one('product.pricelist', ondelete='cascade')
    company_id = fields.Many2one('res.company', related='pricelist_id.company_id')

    #@api.depends('duration', 'unit')
    def _compute_name(self):
        for record in self:
            if not record.name:
                record.name = 'hello' #_("%s %s", record.duration, record.unit)

    @api.depends_context('lang')
    @api.depends('library_fee_period_id')
    def _compute_name(self):
        for pricing in self:
            # TODO in master: use pricing.recurrence_id.duration_display
            pricing.name = _(
                "%s %s",
                pricing.library_fee_period_id.duration,
                pricing._get_unit_label(pricing.library_fee_period_id.duration))

    def _get_unit_label(self, duration):
        """ Get the translated product pricing unit label. """
        # TODO in master: remove in favor of env['sale.temporal.recurrence']_get_unit_label
        if duration is None:
            return ""
        if float_compare(duration, 1.0, precision_digits=2) < 1\
           and not float_is_zero(duration, precision_digits=2):
            singular_labels = {
                'hour': _lt("Hour"),
                'day': _lt("Day"),
                'week': _lt("Week"),
                'month': _lt("Month"),
                'year': _lt("Year"),
            }
            if self.library_fee_period_id.unit in singular_labels:
                return singular_labels[self.library_fee_period_id.unit]
        return dict(
            self.env['oe.library.fees.period']._fields['unit']._description_selection(self.env)
        )[self.library_fee_period_id.unit]
    
    def _compute_description(self):
        for pricing in self:
            description = ""
            if pricing.currency_id.position == 'before':
                description += format_amount(self.env, amount=pricing.price, currency=pricing.currency_id)
            else:
                description += format_amount(self.env, amount=pricing.price, currency=pricing.currency_id)
            description += _("/%s", pricing.library_fee_period_id.unit)
            pricing.description = description

    @api.model
    def _compute_duration_vals(self, start_date, end_date):
        duration = end_date - start_date
        vals = dict(hour=(duration.days * 24 + duration.seconds / 3600))
        vals['day'] = math.ceil(vals['hour'] / 24)
        vals['week'] = math.ceil(vals['day'] / 7)
        duration_diff = relativedelta(end_date, start_date)
        months = 1 if duration_diff.days or duration_diff.hours or duration_diff.minutes else 0
        months += duration_diff.months
        months += duration_diff.years * 12
        vals['month'] = months
        vals['year'] = months/12
        return vals

    def _compute_price(self, duration, unit):
        """Compute the price for a specified duration of the current pricing rule.
        :param float duration: duration in hours
        :param str unit: duration unit (hour, day, week)
        :return float: price
        """
        self.ensure_one()
        if duration <= 0 or self.library_fee_period_id.duration <= 0:
            return self.price
        if unit != self.library_fee_period_id.unit:
            converted_duration = math.ceil((duration * PERIOD_RATIO[unit]) / (self.library_fee_period_id.duration * PERIOD_RATIO[self.library_fee_period_id.unit]))
        else:
            converted_duration = math.ceil(duration / self.library_fee_period_id.duration)
        return self.price * converted_duration

    def _applies_to(self, product):
        """ Check whether current pricing applies to given product.
        :param product.product product:
        :return: true if current pricing is applicable for given product, else otherwise.
        """
        self.ensure_one()
        return (
            self.product_template_id == product.product_tmpl_id
            and (
                not self.product_variant_ids
                or product in self.product_variant_ids))
        
    @api.model
    def _get_suitable_pricings(self, product, pricelist=None, first=False):
        """ Get the suitable pricings for given product and pricelist.

        Note: model method
        """
        is_product_template = product._name == "product.template"
        available_pricings = self.env['oe.library.product.fees']
        if pricelist:
            for pricing in product.product_fees_ids:
                if pricing.pricelist_id == pricelist\
                   and (is_product_template or pricing._applies_to(product)):
                    if first:
                        return pricing
                    available_pricings |= pricing

        for pricing in product.product_fees_ids:
            if not pricing.pricelist_id and (is_product_template or pricing._applies_to(product)):
                if first:
                    return pricing
                available_pricings |= pricing

        return available_pricings



