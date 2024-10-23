# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta, date
from pytz import timezone, UTC

from odoo import api, fields, models, _
from odoo.tools import format_datetime, format_time
from odoo.exceptions import ValidationError, UserError


class LibraryProcessing(models.TransientModel):
    _name = 'oe.library.process.wizard'
    _description = 'Issue/Return Books'

    order_id = fields.Many2one('sale.order', required=True, ondelete='cascade',
                               
                              )
    
    
    wizard_line_ids = fields.One2many('oe.library.process.wizard.line', 'order_wizard_id')
    status = fields.Selection(
        selection=[
            ('issue', 'Issued'),
            ('return', 'Return'),
        ],
    )
    has_late_lines = fields.Boolean(compute='_compute_has_late_lines')

    @api.model
    def default_get(self, fields):
        res = super(LibraryProcessing, self).default_get(fields)
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id', [])
        record_id = self.env[active_model].search([('id','=',active_id)])
        
        #res['order_line_id'] = self._context.get('active_id')
        res['order_id'] = record_id.id
        res['status'] = self.env.context.get('status', [])
        #res['uom_id'] = record_id.product_uom.id
        
        return res

    
    @api.onchange('order_id')
    def _get_wizard_lines(self):
        """Use Wizard lines to set by default the pickup/return value
        to the total pickup/return value expected"""
        #order_line_ids = self.env.context.get('order_line_ids', [])
        #order_lines = self.env['sale.order.line'].browse(order_line_ids)

        order_lines = self.env['sale.order.line'].search([('order_id','=',self.order_id.id),('product_id.is_book','=',True)])
        # generate line values
        #raise ValidationError(order_lines)
        if order_lines:
            lines_values = []
            for line in order_lines:
                lines_values.append(self.env['oe.library.process.wizard.line']._default_wizard_line_vals(line, self.status))

            self.wizard_line_ids = [(6, 0, [])] + [(0, 0, vals) for vals in lines_values]

    @api.depends('wizard_line_ids')
    def _compute_has_late_lines(self):
        for wizard in self:
            wizard.has_late_lines = wizard.wizard_line_ids and any(line.is_book_late for line in wizard.wizard_line_ids)

    def apply(self):
        """Apply the wizard modifications to the SaleOrderLine(s).

        And logs the infos in the SaleOrder chatter
        """
        for wizard in self:
            msg = wizard.wizard_line_ids._apply()
            if msg:
                for key, value in wizard._fields['status']._description_selection(wizard.env):
                    if key == wizard.status:
                        translated_status = value
                        break

                header = "<b>" + translated_status + "</b>:<ul>"
                msg = header + msg + "</ul>"
                wizard.order_id.message_post(body=msg)
        return  # {'type': 'ir.actions.act_window_close'}


class LibraryProcessingLine(models.TransientModel):
    _name = 'oe.library.process.wizard.line'
    _description = 'Library Order Processing transient representation'

    @api.model
    def _default_wizard_line_vals(self, line, status):
        #delay_price = line.product_id._compute_delay_price(fields.Datetime.now() - line.return_date)
        return {
            'order_line_id': line.id,
            'product_id': line.product_id.id,
            'qty_reserved': line.product_uom_qty,
            'qty_delivered': line.qty_delivered if status == 'return' else line.product_uom_qty - line.qty_delivered,
            'book_returned': line.book_returned if status == 'issue' else line.qty_delivered - line.book_returned,
            'is_book_late': line.is_book_late #and delay_price > 0
        }

    order_wizard_id = fields.Many2one('oe.library.process.wizard', 'Order Wizard', required=True, ondelete='cascade')
    status = fields.Selection(related='order_wizard_id.status')

    order_line_id = fields.Many2one('sale.order.line', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    qty_reserved = fields.Float("Reserved")
    qty_delivered = fields.Float("Issued")
    book_returned = fields.Float("Returned")

    is_book_late = fields.Boolean(default=False)  # make related on sol is_book_late ?

    issue_lot_ids = fields.Many2many('stock.lot', 'book_issue_serial_rel',
                    domain="[('product_id','=',product_id)]"
                )
    
    return_lot_ids = fields.Many2many('stock.lot', 'book_return_serial_rel',
                    domain="[('product_id','=',product_id)]", 
                    compute='_compute_all_return',
                )

    @api.onchange('issue_lot_ids')
    def _update_issued_quantity(self):
        for line in self:
            line.qty_delivered = len(line.issue_lot_ids)

    @api.onchange('return_lot_ids')
    def _update_returned_quantity(self):
        for line in self:
            line.book_returned = len(line.return_lot_ids)
    
    @api.depends('status','order_line_id')
    def _compute_all_return(self):
        for line in self:
            line.return_lot_ids = line.order_line_id.library_issue_lot_ids
        
    @api.constrains('book_returned', 'qty_delivered')
    def _only_pickedup_can_be_returned(self):
        for wizard_line in self:
            if wizard_line.status == 'return' and wizard_line.book_returned > wizard_line.qty_delivered:
                raise ValidationError(_("You can't return more than what's been picked-up."))

    def _apply(self):
        """Apply the wizard modifications to the SaleOrderLine.

        :return: message to log on the Sales Order.
        :rtype: str
        """
        msg = self._generate_log_message()
        now = fields.Datetime.now()
        for wizard_line in self:
            order_line = wizard_line.order_line_id
            order_line.mapped('company_id').filtered(lambda company: not company.library_loc_id)._create_library_location()
            if wizard_line.status == 'issue' and wizard_line.qty_delivered > 0:
                if len(wizard_line.issue_lot_ids) == 0:
                    return False
                delivered_qty = order_line.qty_delivered + wizard_line.qty_delivered
                vals = {'qty_delivered': delivered_qty}
                if delivered_qty > order_line.product_uom_qty:
                    vals['product_uom_qty'] = delivered_qty
                if order_line.book_issue_date > now:
                    vals['book_issue_date'] = now
                vals['library_issue_lot_ids'] = wizard_line.issue_lot_ids
                order_line.update(vals)
                order_line.order_id.write({
                    'borrow_status': 'issue',
                })
                lot_ids = wizard_line.issue_lot_ids
                
            elif wizard_line.status == 'return' and wizard_line.book_returned > 0:
                if len(wizard_line.return_lot_ids) == 0:
                    return False
                if wizard_line.order_line_id.is_book_late:
                    # Delays facturation
                    wizard_line._generate_delay_line(wizard_line.book_returned)
                order_line.update({
                    'book_returned': order_line.book_returned + wizard_line.book_returned,
                    'library_returned_lot_ids': wizard_line.return_lot_ids
                })
                order_line.order_id.write({
                    'borrow_status': 'return',
                })
                lot_ids = wizard_line.return_lot_ids
            stock_move_id = self.env['stock.move'].create(self._prepare_stock_move_values(order_line))
            #raise UserError(lot_ids)
            move_lines = []

            if self.status == 'issue':
                library_location = order_line.order_id.company_id.library_loc_id
                stock_location = order_line.order_id.warehouse_id.lot_stock_id
            else:
                stock_location = order_line.order_id.company_id.library_loc_id
                library_location = order_line.order_id.warehouse_id.lot_stock_id
            
            for lot in lot_ids:
                vals = self._prepare_stock_move_line_values(order_line,stock_move_id,lot)
                move_lines.append(vals)
            #raise UserError(len(move_lines))
            stock_move_line_ids = self.env['stock.move.line'].create(move_lines)
            #stock_move_line_id = self.env['stock.move.line'].create(self._prepare_stock_move_line_values(order_line,stock_move_id,lot))
        return msg

    def _prepare_stock_move_values(self,line):
        self.ensure_one()
        if self.status == 'issue':
            library_location = line.order_id.company_id.library_loc_id
            stock_location = line.order_id.warehouse_id.lot_stock_id
        else:
            stock_location = line.order_id.company_id.library_loc_id
            library_location = line.order_id.warehouse_id.lot_stock_id
        return {
            'reference': _('Library Move:' + line.order_id.name),
            'name': _('Library Move:' + line.order_id.name),
            'date': fields.Datetime.now(),
            'location_id': stock_location.id,
            'location_dest_id': library_location.id,
            'company_id': line.order_id.company_id.id,
            'product_id': line.product_id.id,
            'product_uom_qty': self.qty_delivered,
            'warehouse_id': line.order_id.warehouse_id.id,
            'state': 'done',
        }
    def _prepare_stock_move_line_values(self,line, stock_move_id,lot):
        self.ensure_one()
        if self.status == 'issue':
            library_location = line.order_id.company_id.library_loc_id
            stock_location = line.order_id.warehouse_id.lot_stock_id
        else:
            stock_location = line.order_id.company_id.library_loc_id
            library_location = line.order_id.warehouse_id.lot_stock_id
        return {
            'reference': _('Library Move:' + line.order_id.name + lot.name),
            #'name': _('Library Move:' + line.order_id.name),
            'date': fields.Datetime.now(),
            'location_id': stock_location.id,
            'location_dest_id': library_location.id,
            'company_id': line.order_id.company_id.id,
            'product_id': line.product_id.id,
            'quantity': 1,
            #'warehouse_id': line.order_id.warehouse_id.id,
            'lot_id': lot.id,
            'move_id': stock_move_id.id,
            'state': 'done',
        }
        
    def _get_diff(self):
        """Return the quantity changes due to the wizard line.

        :return: (diff, old_qty, new_qty) floats
        :rtype: tuple(float, float, float)
        """
        self.ensure_one()
        order_line = self.order_line_id
        if self.status == 'pickup':
            return self.qty_delivered, order_line.qty_delivered, order_line.qty_delivered + self.qty_delivered
        else:
            return self.book_returned, order_line.book_returned, order_line.book_returned + self.book_returned

    def _generate_log_message(self):
        msg = ""
        for line in self:
            order_line = line.order_line_id
            diff, old_qty, new_qty = line._get_diff()
            if diff:  # i.e. diff>0

                msg += "<li> %s" % (order_line.product_id.display_name)

                if old_qty > 0:
                    msg += ": %s -> <b> %s </b> %s <br/>" % (old_qty, new_qty, order_line.product_uom.name)
                elif new_qty != 1 or order_line.product_uom_qty > 1.0:
                    msg += ": %s %s <br/>" % (new_qty, order_line.product_uom.name)
                # If qty = 1, product has been picked up, no need to specify quantity
                # But if ordered_qty > 1.0: we need to still specify pickedup/returned qty
        return msg

    def _generate_delay_line(self, qty):
        """Generate a sale order line representing the delay cost due to the late return.

        :param float qty:
        :param timedelta duration:
        """
        self.ensure_one()

        self.order_line_id.order_id.update({
            'note': str(fields.Datetime.now()),
        })
        #if qty <= 0 or not self.is_book_late:
        #    return

        duration = fields.Datetime.now() - self.order_line_id.book_return_date

        delay_price = self.product_id._compute_book_delay_price(duration)
        if delay_price <= 0.0:
            return

        
        # migrate to a function on res_company get_extra_product?
        delay_product = self.order_line_id.order_id.company_id.book_charge_product_id
        
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
            self.order_line_id.order_id.company_id.book_charge_product_id = delay_product

        if not delay_product.active:
            return

        delay_price = self.product_id.currency_id._convert(
            from_amount=delay_price,
            to_currency=self.order_line_id.currency_id,
            company=self.order_line_id.order_id.company_id,
            date=date.today(),
        )

        vals = self._prepare_delay_line_vals(delay_product, delay_price, qty)

        self.order_line_id.order_id.write({
            'order_line': [(0, 0, vals)]
        })

    def _prepare_delay_line_vals(self, delay_product, delay_price, qty):
        """Prepare values of delay line.

        :param float delay_price:
        :param float quantity:
        :param delay_product: Product used for the delay_line
        :type delay_product: product.product
        :return: sale.order.line creation values
        :rtype dict:
        """
        delay_line_description = self._get_delay_line_description()
        return {
            'name': delay_line_description,
            'product_id': delay_product.id,
            'product_uom_qty': qty,
            'product_uom': self.product_id.uom_id.id,
            'qty_delivered': qty,
            'price_unit': delay_price,
        }

    def _get_delay_line_description(self):
        # Shouldn't tz be taken from self.order_id.user_id.tz ?
        tz = self._get_tz()
        return "%s\n%s: %s\n%s: %s" % (
            self.product_id.name,
            _("Expected"),
            format_datetime(self.with_context(use_babel=True).env, self.order_line_id.book_return_date, tz=tz, dt_format=False),
            _("Returned"),
            format_datetime(self.with_context(use_babel=True).env, fields.Datetime.now(), tz=tz, dt_format=False)
        )
    def _get_tz(self):
        return self.env.context.get('tz') or self.env.user.tz or 'UTC'
