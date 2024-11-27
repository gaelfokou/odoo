from odoo import fields, models, api, _
from odoo.exceptions import UserError
from . import utils
from datetime import date
import logging
_logger = logging.getLogger("Logger ==========")


class FeeSpecial(models.Model):
    _name = 'siantou.ems.fee.special'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _get_default_acadmic_year(self):
        """Get the default acedemic year active"""

        year = self.env['siantou.ems.core.year'].search(
            [('active', '=', True)], limit=1)

        if not year:
            raise UserError(""" Aucune annéé academique activé, vous ne pouvez pas effectuer la facturation
                            """)
        return year.id

    name = fields.Char('Réference', default='/')

    student_id = fields.Many2one(
        'oe.school.student', string='Etudiant', required=True)

    partner_id = fields.Many2one(
        'res.partner', string='partner', related="student_id.student_enroll_id.partner_id")

    fee_structure_id = fields.Many2one('siantou.ems.fee.structure',
                                       domain=[('fee_special', '=', True)],
                                       string='Catégorie de frais', required=True, tracking=True)

    facture_id = fields.Many2one('account.move',
                                 string='Facture')

    amount = fields.Monetary(
        'Montant total', required=True, tracking=True)

    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id, readonly=True, related_sudo=False)

    campus = fields.Many2one('siantou.ems.core.campus', string="Campus")

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Valider')
    ], string='Etat', default='draft', tracking=True)

    academic_year_id = fields.Many2one('siantou.ems.core.year',
                                       string='Année Académique',
                                       help="Séletionner l'Année Académique",
                                       required=True, default=lambda self: self._get_default_acadmic_year())

    description = fields.Text('Description')

    @api.constrains('amount')
    def _constrains_amount(self):
        """Amount paid less or egal than amount of selected invoice"""
        for rec in self:
            if rec.amount <= 0:
                raise UserError(""" Le montant du frais spécial ne peut être égal à 0
                                """)

    def validate_special(self):
        """Validate, create and match payment and invoice"""
        account_move_obj = self.env['account.move']
        for rec in self:
            student = rec.student_id
            cat = rec.fee_structure_id.category_id
            # for struct in rec.fee_structure_id.fee_type_ids:
            lines = []
            values = {
                'fee_category_id': cat.id,
                'student_id': student.id,
                'fee_structure': rec.fee_structure_id.id,
                'invoice_date': date.today(),
                'class_division_id': student.class_id.id,
                'is_fee': True,
                'partner_id': student.student_id.student_enroll_id.partner_id.id,
                'journal_id': cat.journal_id.id,
                'move_type': 'out_invoice'
            }


            fee_line = {
                'credit': rec.amount,
                'partner_id': student.student_id.student_enroll_id.partner_id.id,
                'price_unit': rec.amount,
                'price_subtotal': rec.amount,
                'price_total': rec.amount,
                'quantity': 1.0,
                # 'product_id': line.fee_type.product_id.id,
                'name': rec.name,
                'account_id': cat.journal_id.default_account_id.id
            }
            lines.append((0, 0, fee_line))
            fee_line2 = {
                'debit': rec.amount,
                'partner_id': student.student_id.student_enroll_id.partner_id.id,
                'price_unit': rec.amount,
                'price_subtotal': rec.amount,
                'price_total': rec.amount,
                'quantity': 1.00,
                'exclude_from_invoice_tab': True,
                'account_id': student.partner_id.property_account_receivable_id.id
            }
            lines.append((0, 0, fee_line2))
            _logger.info(lines)
            values['invoice_line_ids'] = lines
            values['line_ids'] = lines
            move_id = account_move_obj.create(values)
            move_id.action_post()
            _logger.info(lines)
            rec.facture_id = move_id.id

        self.state = 'done'



    def reset_special(self):
        """Cancel payment"""
        for rec in self:
            rec.state = 'draft'

    @api.model
    def create(self, vals):
        """Over riding the create method to assign
        sequence for the newly creating the record"""
        vals['name'] = self.env['ir.sequence'].next_by_code(
            'siantou.ems.fee.special')
        res = super(FeeSpecial, self).create(vals)
        return res
