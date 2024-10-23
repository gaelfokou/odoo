# -*- coding:utf-8 -*-

import base64
import logging

from collections import defaultdict
from markupsafe import Markup

from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta

from odoo import api, Command, fields, models, _
from odoo.addons.de_school_fees.models.browsable_object import BrowsableObject, InputFees, OrderFeeLines, Feeslips, ResultRules
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round, date_utils, convert_file, html2plaintext
from odoo.tools import float_compare, float_is_zero, plaintext2html

from odoo.tools.float_utils import float_compare
from odoo.tools.misc import format_date
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class FeeSlip(models.Model):
    _name = 'oe.feeslip'
    _description = 'Fee Slip'
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']
    _order = 'date_to desc'

    fee_struct_id = fields.Many2one(
        'oe.fee.struct', string='Fee Structure',
        compute='_compute_struct_id', store=True, readonly=False, required=True,
    )
    currency_id = fields.Many2one('res.currency', store=True, 
                                  compute='_compute_currency', readonly=False
                                 )
    use_enrol_contract_lines = fields.Boolean(related='fee_struct_id.use_enrol_contract_lines')
    #struct_type_id = fields.Many2one('hr.payroll.structure.type', related='struct_id.type_id')
    #wage_type = fields.Selection(related='struct_type_id.wage_type')
    name = fields.Char(
        string='Feeslip Name', 
        compute='_compute_name', store=True, readonly=True,
    )
    number = fields.Char(
        string='Reference', readonly=False, copy=False,
    )
    
    student_id = fields.Many2one(
        'res.partner', string='Student', required=True, readonly=False,
        domain="[('is_student', '=', True), ('active', '=', True)]")

    image_128 = fields.Image(related='student_id.image_128')
    image_1920 = fields.Image(related='student_id.image_1920')
    avatar_128 = fields.Image(related='student_id.avatar_128')
    avatar_1920 = fields.Image(related='student_id.avatar_1920')
    
    course_id = fields.Many2one('oe.school.course',related='student_id.course_id')
    batch_id = fields.Many2one('oe.school.course.batch',related='student_id.batch_id')
    
    enrol_order_id = fields.Many2one(
        'sale.order', string='Enrol Contract',
        #domain=lambda self: self._compute_enrol_order_domain(),
        domain="[('partner_id', '=', student_id), ('enrol_status', '=', 'open'), ('is_enrol_order', '=', True)]",
        store=True, readonly=False,
        compute='_compute_enrol_order',
    )
    
    date_from = fields.Date(
        string='From', required=True,
    )
    date_to = fields.Date(
        string='To', required=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('paid', 'Paid'),
        ('cancel', 'Rejected')],
        string='Status', index=True, readonly=True, copy=False,
        compute='_compute_state', store=True,
        default='draft', tracking=True,
        help="""* When the feeslip is created the status is \'Draft\'
                \n* If the feeslip is under verification, the status is \'Waiting\'.
                \n* If the feeslip is confirmed then status is set to \'Done\'.
                \n* When user cancel feeslip the status is \'Rejected\'.""")

    line_ids = fields.One2many(
        'oe.feeslip.line', 'feeslip_id', string='Feeslip Lines',
        compute='_compute_line_ids', store=True, readonly=True, copy=True,
    )
    company_id = fields.Many2one(
        'res.company', string='Company', copy=False, required=True, readonly=True,
        default=lambda self: self.env.company,
    )
    
    enrol_order_line_ids = fields.One2many(
        'oe.feeslip.enrol.order.line', 'feeslip_id', string='feeslip Contract Lines', copy=True,
        compute='_compute_enrol_order_line_ids', store=True, readonly=True,
    )

    input_line_ids = fields.One2many(
        'oe.feeslip.input.line', 'feeslip_id', string='Feeslip Inputs', store=True,
        compute='_compute_input_line_ids', 
        readonly=False
    )
    paid = fields.Boolean(
        string='Made Payment Order ? ', readonly=True, copy=False,
        states={'draft': [('readonly', False)], 'verify': [('readonly', False)]})
    note = fields.Text(string='Internal Note', readonly=False)
   
    credit_note = fields.Boolean(
        string='Credit Note', readonly=False,
        help="Indicates this feeslip has a refund of another")
    has_refund_slip = fields.Boolean(compute='_compute_has_refund_slip')
    feeslip_run_id = fields.Many2one('oe.feeslip.run', string='Batch Name', readonly=True,
        copy=False, ondelete='cascade',
        domain="[('company_id', '=', company_id)]"
    )
    compute_date = fields.Date('Computed On')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    amount_total = fields.Monetary(string="Total", store=True, compute="_compute_amount_total")
    
    is_superuser = fields.Boolean(compute="_compute_is_superuser")
    edited = fields.Boolean()
    queued_for_pdf = fields.Boolean(default=False)

    account_move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=True, copy=False)
    date = fields.Date('Date Account', help="Keep empty to use the period of the validation(Feeslip) date.")

    
    
    #@api.depends('course_id','batch_id','fee_struct_id')
    @api.onchange('course_id','batch_id','fee_struct_id')
    def _find_fee_dates(self):
        today = datetime.today()
        first_day_of_month = today.replace(day=1)

        if self.fee_struct_id:
            self.date_from = first_day_of_month
            schedule_pay_duration = self.fee_struct_id.schedule_pay_duration
            date_to = first_day_of_month + relativedelta(months=schedule_pay_duration)
            self.date_to = date_to - relativedelta(days=1)  # To get the last day of the calculated month
        else:
            self.date_from = first_day_of_month
            last_day_of_month = first_day_of_month + relativedelta(months=1) - relativedelta(days=1)
            self.date_to = last_day_of_month


    @api.depends('student_id')
    def _compute_enrol_order(self):
        for slip in self:
            enrol_order = self.env['sale.order'].search([
                ('partner_id', '=', slip.student_id.id),
                ('enrol_status', '=', 'open'),
                ('is_enrol_order', '=', True)
            ], limit=1)
            slip.enrol_order_id = enrol_order if enrol_order else False
            
    @api.depends('line_ids','line_ids.total')
    def _compute_amount_total(self):
        for record in self:
            record.amount_total = sum(record.line_ids.mapped('total'))
            
    @api.depends('company_id', 'student_id')
    def _compute_enrol_order_domain(self):
        # Define the domain criteria here
        for feeslip in self:
        # Define the domain criteria here
            domain = [
                ('partner_id', '=', feeslip.student_id.id),
                ('enrol_status', '=', 'open'),
                ('is_enrol_order', '=', True),
            ]
            enrol_order_ids = self.env['sale.order'].search(domain)
            feeslip.enrol_order_id = enrol_order_ids
            

    @api.depends('company_id','fee_struct_id')
    def _compute_currency(self):
        for record in self:
            if record.fee_struct_id.journal_id.currency_id:
                record.currency_id = record.fee_struct_id.journal_id.currency_id.id
            else:
                record.currency_id = record.company_id.currency_id.id

    @api.depends(
        'account_move_id',
        'account_move_id.payment_state',
    )
    def _compute_state(self):
        for record in self:
            if record.account_move_id:
                if record.account_move_id.payment_state in ('in_payment', 'paid', 'partial'):
                    record.state = 'paid'
                else:
                    record.state = 'done' 
        
    def _is_invalid(self):
        self.ensure_one()
        if self.state not in ['done', 'paid']:
            return _("This feeslip is not validated. This is not a legal document.")
        return False

    @api.depends('enrol_order_line_ids', 'input_line_ids')
    def _compute_line_ids(self):
        if not self.env.context.get("feeslip_no_recompute"):
            return
        for feeslip in self.filtered(lambda p: p.line_ids and p.state in ['draft', 'verify']):
            feeslip.line_ids = [(5, 0, 0)] + [(0, 0, line_vals) for line_vals in feeslip._get_feeslip_lines()]

    def _compute_is_superuser(self):
        self.update({'is_superuser': self.env.user._is_superuser() and self.user_has_groups("base.group_no_one")})

    def _compute_has_refund_slip(self):
        #This field is only used to know whether we need a confirm on refund or not
        #It doesn't have to work in batch and we try not to search if not necessary
        for feeslip in self:
            if not feeslip.credit_note and feeslip.state in ('done', 'paid') and self.search_count([
                ('student_id', '=', feeslip.student_id.id),
                ('date_from', '=', feeslip.date_from),
                ('date_to', '=', feeslip.date_to),
                #('enrol_order_id', '=', feeslip.enrol_order_id.id),
                ('fee_struct_id', '=', feeslip.fee_struct_id.id),
                ('credit_note', '=', True),
                ('state', '!=', 'cancel'),
                ]):
                feeslip.has_refund_slip = True
            else:
                feeslip.has_refund_slip = False

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        if any(feeslip.date_from > feeslip.date_to for feeslip in self):
            raise ValidationError(_("Feeslip 'Date From' must be earlier 'Date To'."))

    def write(self, vals):
        res = super().write(vals)
        return res

    def action_feeslip_draft(self):
        return self.write({'state': 'draft'})

    def _get_pdf_reports(self):
        classic_report = self.env.ref('hr_payroll.action_report_feeslip')
        result = defaultdict(lambda: self.env['oe.feeslip'])
        for feeslip in self:
            if not feeslip.fee_struct_id or not feeslip.fee_struct_id.report_id:
                result[classic_report] |= feeslip
            else:
                result[feeslip.fee_struct_id.report_id] |= feeslip
        return result

    def _generate_pdf(self):
        mapped_reports = self._get_pdf_reports()
        attachments_vals_list = []
        generic_name = _("feeslip")
        template = self.env.ref('hr_payroll.mail_template_new_feeslip', raise_if_not_found=False)
        for report, feeslips in mapped_reports.items():
            for feeslip in feeslips:
                pdf_content, dummy = report.sudo()._render_qweb_pdf(feeslip.id)
                if report.print_report_name:
                    pdf_name = safe_eval(report.print_report_name, {'object': feeslip})
                else:
                    pdf_name = generic_name
                attachments_vals_list.append({
                    'name': pdf_name,
                    'type': 'binary',
                    'raw': pdf_content,
                    'res_model': feeslip._name,
                    'res_id': feeslip.id
                })
                # Send email to employees
                if template:
                    template.send_mail(feeslip.id, notif_layout='mail.mail_notification_light')
        self.env['ir.attachment'].sudo().create(attachments_vals_list)

    # Fee slip done start

    def action_feeslip_done(self):
        self._validate_feeslips()
        self.write({'state': 'done'})
        self._handle_feeslip_pdf_generation()
        self._action_create_fee_invoice()
        return True

    def _validate_feeslips(self):
        invalid_feeslips = self.filtered(lambda p: not p.enrol_order_id)
        if invalid_feeslips:
            raise ValidationError(_('The following students have an enrol order outside of the feeslip period:\n%s', '\n'.join(invalid_feeslips.mapped('student_id.name'))))
        if any(slip.enrol_order_id.state == 'cancel' for slip in self):
            raise ValidationError(_('You cannot validate a feeslip on which the contract is cancelled'))
        if any(slip.state == 'cancel' for slip in self):
            raise ValidationError(_("You can't validate a cancelled feeslip."))

    def _handle_feeslip_pdf_generation(self):
        if self.env.context.get('feeslip_generate_pdf'):
            if self.env.context.get('feeslip_generate_pdf_direct'):
                self._generate_pdf()
            else:
                self.write({'queued_for_pdf': True})
                feeslip_cron = self.env.ref('de_school_fees.ir_cron_generate_feeslip_pdfs', raise_if_not_found=False)
                if feeslip_cron:
                    feeslip_cron._trigger()

    def _action_create_fee_invoice(self):
        feeslips_to_post = self._get_feeslips_to_post()
        self._validate_journals(feeslips_to_post)
        
        slip_mapped_data = self._map_feeslips_by_journal(feeslips_to_post)

        for journal_id, slips in slip_mapped_data.items():
            move_dict = self._prepare_move_dict(journal_id, slips)
            line_ids = self._prepare_all_slip_lines(slips, move_dict['date'])
            move_dict['line_ids'] = [(0, 0, line_vals) for line_vals in line_ids]

            move = self._create_account_move(move_dict)
            move.sudo().action_post()
            self._assign_account_move_to_slips(slips, move)

    def _get_feeslips_to_post(self):
        feeslips_to_post = self.filtered(lambda slip: not slip.feeslip_run_id)

        feeslip_runs = (self - feeslips_to_post).mapped('feeslip_run_id')
        for run in feeslip_runs:
            if run._are_feeslips_ready():
                feeslips_to_post |= run.slip_ids

        feeslips_to_post = feeslips_to_post.filtered(lambda slip: slip.state == 'done' and not slip.account_move_id)
        return feeslips_to_post

    def _validate_journals(self, feeslips_to_post):
        if any(not feeslip.fee_struct_id for feeslip in feeslips_to_post):
            raise ValidationError(_('One of the contracts for these feeslips has no structure type.'))
        if any(not structure.journal_id for structure in feeslips_to_post.mapped('fee_struct_id')):
            raise ValidationError(_('One of the feeslips structures has no account journal defined on it.'))

    def _map_feeslips_by_journal(self, feeslips_to_post):
        slip_mapped_data = defaultdict(list)
        for slip in feeslips_to_post:
            slip_mapped_data[slip.fee_struct_id.journal_id.id].append(slip)
        return slip_mapped_data

    def _prepare_move_dict(self, journal_id, slips):
        date = fields.Date().end_of(slips[0].date_to, 'month')
        move_dict = {
            'narration': '',
            'ref': date.strftime('%B %Y'),
            'journal_id': journal_id,
            'move_type': 'out_invoice',
            'date': date,
            'invoice_date': date,
            'partner_id': slips[0].student_id.id,
        }
        for slip in slips:
            move_dict['narration'] += plaintext2html(slip.number or '' + ' - ' + slip.student_id.name or '')
            move_dict['narration'] += Markup('<br/>')
        return move_dict

    def _prepare_all_slip_lines(self, slips, date):
        line_ids = []
        for slip in slips:
            slip_lines = slip._prepare_slip_lines(date)
            line_ids.extend(slip_lines)
        return line_ids

    def _prepare_line_values(self, line, product_id, date, quantity, price_unit):
        sale_line_id = self.env['sale.order.line'].search([
            ('order_id', '=', line.feeslip_id.enrol_order_id.id),
            ('product_id', '=', product_id)
        ], limit=1)

        if not sale_line_id:
            sale_order_line_values = {
                'order_id': line.feeslip_id.enrol_order_id.id,
                'product_id': product_id,
                'name': line.name,
                'product_uom_qty': quantity,
                'price_unit': price_unit,
                'qty_delivered': 0.0,
                'qty_invoiced': quantity,
                'is_downpayment': True,
            }
            sale_line_id = self.env['sale.order.line'].create(sale_order_line_values)

        return {
            'name': line.name,
            'partner_id': line.student_id.id,
            'journal_id': line.feeslip_id.fee_struct_id.journal_id.id,
            'date': date,
            'product_id': product_id,
            'quantity': quantity,
            'price_unit': price_unit,
            'sale_line_ids': [(4, sale_line_id.id)],
        }

    def _prepare_slip_lines(self, date):
        self.ensure_one()
        new_lines = []
        for line in self.line_ids.filtered(lambda x: x.fee_rule_id.product_id):
            product_id = line.fee_rule_id.product_id.id
            quantity = line.quantity
            price_unit = line.total
            fee_line = self._prepare_line_values(line, product_id, date, quantity, price_unit)
            new_lines.append(fee_line)
        return new_lines

    def _create_account_move(self, values):
        return self.env['account.move'].sudo().create(values)

    def _assign_account_move_to_slips(self, slips, move):
        date = move.date
        for slip in slips:
            slip.write({'account_move_id': move.id, 'date': date})
            
    # fee slip done end
        
        
    def action_feeslip_cancel(self):
        if not self.env.user._is_system() and self.filtered(lambda slip: slip.state == 'done'):
            raise UserError(_("Cannot cancel a feeslip that is done."))
        self.mapped('feeslip_run_id').action_close()
        self.account_move_id.sudo().button_draft()
        self.account_move_id.sudo().button_cancel()
        self.write({
            'state': 'cancel',
            'account_move_id': False,
        })

    def action_feeslip_paid(self):
        if any(slip.state != 'done' for slip in self):
            raise UserError(_('Cannot mark feeslip as paid if not confirmed.'))
        
        # Update account_move_id field in FeeSlip
        self.write({
            'state': 'paid'
        })


    def refund_sheet(self):
        pass

    @api.ondelete(at_uninstall=False)
    def _unlink_if_draft_or_cancel(self):
        if any(feeslip.state not in ('draft', 'cancel') for feeslip in self):
            raise UserError(_('You cannot delete a feeslip which is not draft or cancelled!'))

    def compute_sheet(self):
        feeslips = self.filtered(lambda slip: slip.state in ['draft', 'verify'])
        # delete old feeslip lines
        feeslips.line_ids.unlink()
        for feeslip in feeslips:
            number = feeslip.number or self.env['ir.sequence'].next_by_code('fee.slip')
            lines = [(0, 0, line) for line in feeslip._get_feeslip_lines()]
            feeslip.write({'line_ids': lines, 'number': number, 'state': 'verify', 'compute_date': fields.Date.today()})
        
        #return True

    def _get_base_local_dict(self):
        return {
            'float_round': float_round,
            'float_compare': float_compare,
        }

    def _get_localdict(self):
        self.ensure_one()
        order_fee_lines_dict = {line.code: line for line in self.enrol_order_line_ids if line.code}
        inputs_dict = {line.code: line for line in self.input_line_ids if line.code}

        student = self.student_id
        enrol_order = self.enrol_order_id

        localdict = {
            **self._get_base_local_dict(),
            **{
                'categories': BrowsableObject(student.id, {}, self.env),
                'rules': BrowsableObject(student.id, {}, self.env),
                'feeslip': Feeslips(student.id, self, self.env),
                'order_fee': OrderFeeLines(student.id, order_fee_lines_dict, self.env),
                'inputfee': InputFees(student.id, inputs_dict, self.env),
                'student': student,
                'result_rules': ResultRules(student.id, {}, self.env)
            }
        }
        return localdict

    def _get_feeslip_lines(self):
        self.ensure_one()

        localdict = self.env.context.get('force_feeslip_localdict', None)

        
        if localdict is None:
            localdict = self._get_localdict()

        rules_dict = localdict['rules'].dict
        result_rules_dict = localdict['result_rules'].dict

        blacklisted_rule_ids = self.env.context.get('prevent_feeslip_computation_line_ids', [])

        result = {}

        for rule in sorted(self.fee_struct_id.rule_ids, key=lambda x: x.sequence):
            if rule.id in blacklisted_rule_ids:
                continue
            localdict.update({
                'result': None,
                'result_qty': 1.0,
                'result_rate': 100,
                'result_name': False
            })
            if rule._satisfy_condition(localdict):
                amount, qty, rate = rule._compute_rule(localdict)
                #check if there is already a rule computed with that code
                previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                #set/overwrite the amount computed for this rule in the localdict
                tot_rule = amount * qty * rate / 100.0
                localdict[rule.code] = tot_rule
                result_rules_dict[rule.code] = {'total': tot_rule, 'amount': amount, 'quantity': qty}
                rules_dict[rule.code] = rule
                # sum the amount for its salary category
                localdict = rule.category_id._sum_fee_category(localdict, tot_rule - previous_amount)
                # Retrieve the line name in the employee's lang
                employee_lang = self.student_id.sudo().lang
                # This actually has an impact, don't remove this line
                context = {'lang': employee_lang}
                if localdict['result_name']:
                    rule_name = localdict['result_name']
                elif rule.code in ['BASIC', 'GROSS', 'NET', 'DEDUCTION', 'REIMBURSEMENT']:  # Generated by default_get (no xmlid)
                    if rule.code == 'BASIC':  # Note: Crappy way to code this, but _(foo) is forbidden. Make a method in master to be overridden, using the structure code
                        if rule.name == "Double Holiday Pay":
                            rule_name = _("Double Holiday Pay")
                        if rule.fee_struct_id.name == "CP200: Employees 13th Month":
                            rule_name = _("Prorated end-of-year bonus")
                        else:
                            rule_name = _('Basic Salary')
                    elif rule.code == "GROSS":
                        rule_name = _('Gross')
                    elif rule.code == "DEDUCTION":
                        rule_name = _('Deduction')
                    elif rule.code == "REIMBURSEMENT":
                        rule_name = _('Reimbursement')
                    elif rule.code == 'NET':
                        rule_name = _('Net Salary')
                else:
                    rule_name = rule.with_context(lang=employee_lang).name
                # create/overwrite the rule in the temporary results
                result[rule.code] = {
                    'sequence': rule.sequence,
                    'code': rule.code,
                    'name': rule_name,
                    'note': html2plaintext(rule.note),
                    'fee_rule_id': rule.id,
                    #'enrol_order_id': localdict['enrol_order'].id,
                    'student_id': localdict['student'].id,
                    'amount': amount,
                    'quantity': qty,
                    'rate': rate,
                    'feeslip_id': self.id,
                }
        return result.values()

    @api.depends('student_id', 'date_from', 'date_to')
    def _compute_enrol_order_id(self):
        for slip in self:
            if not slip.student_id or not slip.date_from or not slip.date_to:
                slip.enrol_order_id = False
                continue
            # Add a default enrol_order if not already defined or invalid
            if slip.enrol_order_id and slip.student_id == slip.enrol_order_id.student_id:
                continue
            enrol_orders = False #slip.student_id._get_enrol_orders(slip.date_from, slip.date_to)
            slip.enrol_order_id = enrol_orders[0] if enrol_orders else False

    @api.depends('course_id','batch_id', 'student_id')
    def _compute_struct_id(self):
        for slip in self:
            fee_struct = self.env['oe.fee.struct'].search([
                ('course_id', '=', slip.course_id.id),
                ('pay_one_time', '=', False), 
                '|',
                ('batch_ids', 'in', slip.batch_id.id),
                ('batch_ids', '=', False)
            ], limit=1)
            #raise UserError(fee_struct)
            slip.fee_struct_id = fee_struct if fee_struct else False

    @api.depends('student_id', 'fee_struct_id', 'date_from','date_to')
    def _compute_name(self):
        for slip in self.filtered(lambda p: p.student_id and p.date_from):
            lang = slip.student_id.sudo().lang or self.env.user.lang
            context = {'lang': lang}
            feeslip_name = slip.fee_struct_id.feeslip_name or _('Fee Slip')
            del context

            slip.name = '%(feeslip_name)s - %(employee_name)s (%(date_from)s - %(date_to)s)' % {
                'feeslip_name': feeslip_name,
                'employee_name': slip.student_id.name,
                'date_from': format_date(self.env, slip.date_from, date_format="MMMM y", lang_code=lang),
                'date_to': format_date(self.env, slip.date_to, date_format="MMMM y", lang_code=lang)
            }

    @api.depends('student_id', 'enrol_order_id')
    def _compute_enrol_order_line_ids(self):
        valid_slips = self.filtered(lambda p: p.student_id)
        if not valid_slips:
            return
        self.update({'enrol_order_line_ids': [(5, 0, 0)]})
        if not valid_slips:
            return

        for slip in valid_slips:
            slip.update({'enrol_order_line_ids': slip._get_new_enrol_order_lines()})


    def _get_new_enrol_order_lines(self):
        sale_order = self.enrol_order_id
        if sale_order:
            sale_order_lines = sale_order.order_line
            enrol_order_line_data = [(0, 0, {
                'name': line.name,
                'sequence': 10,
                'product_id': line.product_id.id,
                'code': line.product_id.default_code,
                'amount': line.price_total,
                'quantity': line.product_uom_qty,
                'price_unit': line.price_unit,
                'qty_invoiced': line.qty_invoiced,
                'qty_to_invoice': line.qty_to_invoice,
                'order_line_id': line.id,
            }) for line in sale_order_lines]

            return enrol_order_line_data
        return []

        
    @api.depends('student_id', 'fee_struct_id')
    def _compute_input_line_ids(self):
        valid_slips = self.filtered(lambda p: p.student_id and p.fee_struct_id)
        if not valid_slips:
            return
        self.update({'input_line_ids': [(5, 0, 0)]})
        if not valid_slips:
            return

        for slip in valid_slips:
            slip.update({'input_line_ids': slip._get_new_input_lines()})

    def _get_new_input_lines(self):
        struct_id = self.fee_struct_id
        if struct_id:
            other_lines = struct_id.input_line_type_ids
            other_line_data = []
    
            for line in other_lines:
                if line.account_journal_id:
                    moves = self.env['account.move'].search([
                        ('partner_id', '=', self.student_id.id),
                        ('journal_id', '=', line.account_journal_id.id),
                        ('state', '=', 'posted'),
                        ('payment_state', 'not in', ['paid', 'reversed','in_payment'])
                    ])
                    if moves:
                        due_amount = sum(moves.mapped('amount_residual_signed'))
                        description = f"Due Amount for {line.name}"
                        other_line_data.append((0, 0, {
                            'name': description,
                            'sequence': 10,
                            'input_type_id': line.id,
                            'code': line.code,
                            'amount': due_amount,
                        }))
                    else:
                        other_line_data.append((0, 0, {
                            'name': line.name,
                            'sequence': 10,
                            'input_type_id': line.id,
                            'code': line.code,
                            'amount': 0,
                        }))
                else:
                    other_line_data.append((0, 0, {
                        'name': line.name,
                        'sequence': 10,
                        'input_type_id': line.id,
                        'code': line.code,
                        'amount': 0,
                    }))
            
            return other_line_data
        return []



    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super().fields_view_get(view_id, view_type, toolbar, submenu)
        if toolbar and 'print' in res['toolbar']:
            res['toolbar'].pop('print')
        return res

    def action_print_feeslip(self):
        return {
            'name': 'Feeslip',
            'type': 'ir.actions.act_url',
            'url': '/print/feeslips?list_ids=%(list_ids)s' % {'list_ids': ','.join(str(x) for x in self.ids)},
        }

    def action_export_feeslip(self):
        self.ensure_one()
        return {
            "name": "Debug Feeslip",
            "type": "ir.actions.act_url",
            "url": "/debug/feeslip/%s" % self.id,
        }

    def _is_outside_enrol_order_dates(self):
        self.ensure_one()
        feeslip = self
        #enrol_order = self.enrol_order_id
        return enrol_order.date_start > feeslip.date_to or (enrol_order.date_end and enrol_order.date_end < feeslip.date_from)

    def _get_data_files_to_update(self):
        # Note: Use lists as modules/files order should be maintained
        return []

    def _update_payroll_data(self):
        data_to_update = self._get_data_files_to_update()
        _logger.info("Update payroll static data")
        idref = {}
        for module_name, files_to_update in data_to_update:
            for file_to_update in files_to_update:
                convert_file(self.env.cr, module_name, file_to_update, idref)

    @api.model
    def _cron_generate_pdf(self):
        feeslips = self.search([
            ('state', 'in', ['done', 'paid']),
            ('queued_for_pdf', '=', True),
        ])
        if not feeslips:
            return
        BATCH_SIZE = 50
        feeslips_batch = feeslips[:BATCH_SIZE]
        feeslips_batch._generate_pdf()
        feeslips_batch.write({'queued_for_pdf': False})
        # if necessary, retrigger the cron to generate more pdfs
        if len(feeslips) > BATCH_SIZE:
            self.env.ref('hr_payroll.ir_cron_generate_feeslip_pdfs')._trigger()

