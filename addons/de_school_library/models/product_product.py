# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _get_best_library_fee_rule(self, **kwargs):
        """Return the best pricing rule for the given duration.

        :return: least expensive pricing rule for given duration
        :rtype: product.pricing
        """
        return self.product_tmpl_id._get_best_library_fee_rule(product=self, **kwargs)

    def action_product_tmpl_forecast_report(self):
        self.ensure_one()
        if self.env.ref('stock.stock_replenishment_product_template_action', raise_if_not_found=False):
            action = self.env["ir.actions.actions"]._for_xml_id('stock.stock_replenishment_product_template_action')
        else:
            action = self.env["ir.actions.actions"]._for_xml_id('stock.stock_replenishment_product_product_action')
        return action

    def _compute_book_delay_price(self, duration):
        """Compute daily and hourly delay price.

        :param timedelta duration: datetime representing the delay.
        """
        days = duration.days
        hours = duration.seconds // 3600
        return days * self.book_charge_daily + hours * self.book_charge_hourly
