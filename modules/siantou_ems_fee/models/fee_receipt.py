# -*- coding: utf-8 -*-


import datetime
from xml.dom import ValidationErr
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class FeeReceipts(models.Model):
    _inherit = 'account.move'
    
    def _get_default_acadmic_year(self):
        """Get the default acedemic year active"""
        
        year = self.env['siantou.ems.core.year'].search([('active', '=', True)], limit=1)
        
        if not year:
            raise UserError(""" Aucune annéé academique activé, vous ne pouvez pas effectuer la facturation
                            """)
        
        return year.id

    @api.onchange('fee_structure')
    def _get_fee_lines(self):
        """Set default fee lines based on selected fee structure"""
        lines = []
        for item in self:
            for line in item.fee_structure.fee_type_ids:
                name = line.fee_type.product_id.description_sale
                if not name:
                    name = line.fee_type.product_id.name
                fee_line = {
                    'credit': line.fee_amount,
                    'price_unit': line.fee_amount,
                    'price_subtotal': line.fee_amount,
                    'price_total': line.fee_amount,
                    'quantity': 1.00,
                    'product_id': line.fee_type.product_id,
                    'name': name,
                    'account_id': item.journal_id.default_account_id
                }
                lines.append((0, 0, fee_line))
                fee_line2 = {
                    'debit': line.fee_amount,
                    'price_unit': line.fee_amount,
                    'price_subtotal': line.fee_amount,
                    'price_total': line.fee_amount,
                    'quantity': 1.00,
                    'exclude_from_invoice_tab': True,
                    'account_id': item.partner_id.property_account_receivable_id
                }
                lines.append((0, 0, fee_line2))
            item.invoice_line_ids = lines

    @api.onchange('student_id', 'fee_category_id', 'payed_from_date', 'payed_to_date')
    def _get_partner_details(self):
        """Student_id is inherited from res_partner. Set partner_id from student_id """
        self.ensure_one()
        lines = []
        for item in self:
            item.invoice_line_ids = lines
            item.partner_id = item.student.student_id.student_enroll_id.partner_id.id
            item.class_division_id = item.student_id.field_of_study_id
            date_today = datetime.date.today()
            company = self.env.user.company_id
            from_date = item.payed_from_date
            to_date = item.payed_to_date
            if not from_date:
                from_date = company.compute_fiscalyear_dates(date_today)['date_from']
            if not to_date:
                to_date = date_today
            if item.partner_id and item.fee_category_id:
                invoice_ids = self.env['account.move'].search([
                    ('partner_id', '=', item.partner_id.id),
                    ('invoice_date', '>=', from_date),
                    ('invoice_date', '<=', to_date),
                    ('fee_category_id', '=', item.fee_category_id.id)])
                invoice_line_list = []
                for invoice in invoice_ids:
                    for line in invoice.invoice_line_ids:
                        fee_line = {
                            'price_unit': line.price_unit,
                            'quantity': line.quantity,
                            'product_id': line.product_id,
                            'price_subtotal': line.price_subtotal,
                            'tax_ids': line.tax_ids,
                            'discount': line.discount,
                            'receipt_no': line.move_name,
                            'date': line.move_id.invoice_date,
                        }
                        invoice_line_list.append((0, 0, fee_line))
                item.payed_line_ids = invoice_line_list


    @api.onchange('fee_category_id')
    def _get_fee_structure(self):
        """ Set domain for fee structure based on category"""
        self.invoice_line_ids = None
        return {
            'domain': {
                'fee_structure': [('category_id', '=', self.fee_category_id.id)]

            }
        }

    @api.onchange('fee_category_id')
    def _get_category_details(self):
        for item in self:
            if item.fee_category_id:
                line = self.fee_category_id.journal_id
                item.journal_id = line

    journal_id = fields.Many2one('account.journal', string='Journal', required=True,)
    student_id = fields.Many2one('oe.school.student', string='Etudiant')
    student_name = fields.Char(string="Nom de l'étudiant", related='student_id.student_enroll_id.partner_id.name', store=True)
    class_division_id = fields.Many2one('siantou.ems.core.field_of_study', string='Filière')
    fee_structure = fields.Many2one('siantou.ems.fee.structure', string='Structure paiement')
    is_fee = fields.Boolean(string='Est un Frais', store=True, default=False)
    fee_category_id = fields.Many2one('siantou.ems.fee.category', string='Catégorie')
    is_fee_structure = fields.Boolean('Possède une structure ?', related='fee_category_id.fee_structure')
    payed_line_ids = fields.One2many('payed.lines', 'partner_id', string='Paiements fait',
                                     readonly=True, store=False)
    payed_from_date = fields.Date(string='Date debut')
    payed_to_date = fields.Date(string='Date fin')
    account_id = fields.Many2one('account.account', string='Compte',
                                 index=True, ondelete="cascade",
                                 domain="[('deprecated', '=', False),"
                                        " ('company_id', '=', 'company_id')"
                                        ",('is_off_balance', '=', False)]",
                                  
                                 tracking=True)
    partner_id = fields.Many2one('res.partner')
    
    academic_year_id = fields.Many2one('siantou.ems.core.year',
                                       string='Année Académique',
                                       help="Séletionner l'Année Académique",
                                       required=True, default=lambda self: self._get_default_acadmic_year())

    @api.model
    def create(self, vals):
        """ Adding two field to invoice. is_fee use to display fee items only in fee tree view"""
        partner = self.env['res.partner'].browse(vals.get('partner_id'))
        if vals.get('fee_category_id'):
            vals.update({
                'is_fee': True,
                'student_name': partner.name
            })
        res = super(FeeReceipts, self).create(vals)
        return res


class InvoiceLineInherit(models.Model):
    _inherit = 'account.move.line'

    manual = fields.Boolean(default=True)

    @api.onchange('product_id')
    def _get_category_domain(self):
        """Set domain for invoice lines depend on selected category"""
        if self.move_id.fee_category_id:
            fee_types = self.env['siantou.ems.fee.type'].search([('category_id', '=', self.move_id.fee_category_id.id)])
            fee_list = []
            for fee in fee_types:
                fee_list.append(fee.product_id.id)
            vals = {
                'domain': {
                    'product_id': [('id', 'in', tuple(fee_list))]
                }
            }
            return vals


# class PayedLinens(models.Model):
#     _name = 'payed.lines'
#     _inherit = 'account.move.line'

#     date = fields.Date(string='Date', readonly=True)
#     receipt_no = fields.Char('Reçu No')
