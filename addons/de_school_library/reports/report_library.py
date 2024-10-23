# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, tools


class LibraryReport(models.Model):
    _name = "oe.library.report"
    _description = "Library Analysis Report"
    _auto = False

    date = fields.Date('Date', readonly=True)
    order_id = fields.Many2one('sale.order', 'Order #', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure', readonly=True)
    quantity = fields.Float('Daily Ordered Qty', readonly=True)
    qty_delivered = fields.Float('Daily Issued Qty', readonly=True)
    qty_returned = fields.Float('Daily Returned Qty', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Customer', readonly=True)
    user_id = fields.Many2one('res.users', 'Salesman', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', readonly=True)
    categ_id = fields.Many2one('product.category', 'Product Category', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm','Confirm'), 
        ('reserve','Reserve'), # Reserve book will hold the book and will not avaible for issuance.
        ('issue','Issued'), # book issue to petron.
        ('return', 'Returned'), # book return by petron.
        ('done', 'Done'), # agreement closed 
        ('cancel', 'Cancelled'), 
    ], string='Status', readonly=True)
    price = fields.Float('Daily Amount', readonly=True)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True)


    def _quantity(self):
        return """
            sol.product_uom_qty / (u.factor * u2.factor) AS quantity,
            sol.qty_delivered / (u.factor * u2.factor) AS qty_delivered,
            sol.book_returned / (u.factor * u2.factor) AS qty_returned
        """

    def _price(self):
        return """
            sol.price_subtotal / (date_part('day',sol.book_return_date - sol.book_issue_date) + 1)
        """

    def _select(self):
        return """
            sol.id,
            sol.order_id,
            sol.product_id,
            %s,
            sol.product_uom,
            sol.order_partner_id AS partner_id,
            sol.salesman_id AS user_id,
            pt.categ_id,
            p.product_tmpl_id,
            generate_series(sol.book_issue_date::date, sol.book_return_date::date, '1 day'::interval)::date date,
            %s AS price,
            sol.company_id,
            o.borrow_status as state,
            sol.currency_id
        """% (self._quantity(), self._price())

    def _from(self):
        return """
            sale_order_line AS sol
            join sale_order o on sol.order_id = o.id
            join product_product AS p on p.id=sol.product_id
            join product_template AS pt on p.product_tmpl_id=pt.id
            join uom_uom AS u on u.id=sol.product_uom
            join uom_uom AS u2 on u2.id=pt.uom_id
        """

    def _query(self):
        return """
            (SELECT %s
            FROM %s
            WHERE o.is_borrow_order)
        """ % (
            self._select(),
            self._from()
        )

    def init(self):
        # self._table = sale_rental_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))
