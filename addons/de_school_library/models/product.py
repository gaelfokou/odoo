# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    is_book = fields.Boolean('Is Book')
    isbn_no = fields.Char('ISBN',
        help='(International Standard Book Number): A unique identifier for the book.',
                         )
    edition_book = fields.Char('Book Edition')
    genre_id = fields.Many2one(
        comodel_name='oe.library.genre',
        string="Genre",
        ondelete='restrict')
    book_lang_id = fields.Many2one('res.lang', string='Language')
    book_pages = fields.Integer(string='Page Count', default=1)
    
    publisher_id = fields.Many2one(
        comodel_name='res.partner',
        domain="[('is_publisher','=',True)]",
        string="Publisher",
        change_default=True, ondelete='restrict')
    author_id = fields.Many2one(
        comodel_name='res.partner',
        domain="[('is_author','=',True)]",
        string="Author",
        change_default=True, ondelete='restrict')
    date_publish = fields.Date('Publication Date')
    product_fees_ids = fields.One2many('oe.library.product.fees', 'product_template_id', string="Library Fees", auto_join=True, copy=True)

    book_charge_hourly = fields.Float("Charge Hour", help="Fine by hour overdue", company_dependent=True)
    book_charge_daily = fields.Float("Charge Day", help="Fine by day overdue", company_dependent=True)

    def _get_best_library_fee_rule(
        self, product=False, start_date=False, end_date=False, duration=False, unit='', **kwargs
    ):
        """ Return the best pricing rule for the given duration.

        :param ProductProduct product: a product recordset (containing at most one record)
        :param float duration: duration, in unit uom
        :param str unit: duration unit (hour, day, week)
        :param datetime start_date: start date of leasing period
        :param datetime end_date: end date of leasing period
        :return: least expensive pricing rule for given duration
        """
        self.ensure_one()
        best_pricing_rule = self.env['oe.library.product.fees']
        if not self.product_fees_ids:
            return best_pricing_rule
        # Two possibilities: start_date and end_date are provided or the duration with its unit.
        pricelist = kwargs.get('pricelist', self.env['product.pricelist'])
        currency = kwargs.get('currency', self.currency_id)
        company = kwargs.get('company', self.env.company)
        duration_dict = {}
        if start_date and end_date:
            duration_dict = self.env['oe.library.product.fees']._compute_duration_vals(start_date, end_date)
        elif not (duration and unit):
            return best_pricing_rule  # no valid input to compute duration.
        min_price = float("inf")  # positive infinity
        Pricing = self.env['oe.library.product.fees']
        available_pricings = Pricing._get_suitable_pricings(product or self, pricelist=pricelist)
        for pricing in available_pricings:
            if duration and unit:
                price = pricing._compute_price(duration, unit)
            else:
                price = pricing._compute_price(duration_dict[pricing.library_fee_period_id.unit], pricing.library_fee_period_id.unit)
            if pricing.currency_id != currency:
                price = pricing.currency_id._convert(
                    from_amount=price,
                    to_currency=currency,
                    company=company,
                    date=fields.Date.today(),
                )
            # We compare the abs of prices because negative pricing (as a promotion) would trigger the
            # highest discount without it.
            if abs(price) < abs(min_price):
                min_price, best_pricing_rule = price, pricing
        return best_pricing_rule

    
    
    