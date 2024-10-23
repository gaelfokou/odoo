# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime, date, time
from dateutil.relativedelta import relativedelta
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import format_date

class FeeslipStudents(models.TransientModel):
    _name = 'oe.feeslip.students'
    _description = 'Generate feeslips for all selected students'

    def _get_available_student_domain(self):
        return [('is_student', '=', True)]

    def _get_students(self):
        active_student_ids = self.env.context.get('active_student_ids', False)
        if active_student_ids:
            return self.env['res.partner'].browse(active_student_ids)
        return self.env['res.partner'].search(self._get_available_student_domain())

    feeslip_run_id = fields.Many2one('oe.feeslip.run', string='Batch Name', readonly=True,
                                     default=lambda self: self.env.context.get('active_id'))

    student_ids_domain = fields.Many2many('res.partner', compute='_compute_student_ids_domain')
    student_ids = fields.Many2many('res.partner', 'oe_student_group_rel', 'feeslip_id', 'student_id', 'Students',
                                   store=True, readonly=False)

    fee_struct_id = fields.Many2one('oe.fee.struct', string='Fee Structure')

    wizard_line = fields.One2many(
        comodel_name='oe.feeslip.students.line',
        inverse_name='wizard_id',
        string="Wizard Lines",
        auto_join=True)

    @api.model
    def default_get(self, fields):
        res = super(FeeslipStudents, self).default_get(fields)
        if 'fee_struct_id' in self._context:
            res['fee_struct_id'] = self._context.get('fee_struct_id')
        return res

    @api.onchange('feeslip_run_id')
    def _onchange_feeslip_run_id(self):
        for record in self:
            record.fee_struct_id = record.feeslip_run_id.fee_struct_id.id

            domain = [('course_id', '=', record.feeslip_run_id.fee_struct_id.course_id.id)]

            if record.feeslip_run_id.fee_struct_id.batch_ids:
                batch_domain = [('batch_id', 'in', record.feeslip_run_id.fee_struct_id.batch_ids.ids)]
                domain = expression.AND([domain, batch_domain])

            record.student_ids = self.env['res.partner'].search(domain)

            # Call method to generate wizard lines
            record.generate_wizard_lines()

    @api.depends('feeslip_run_id')
    def _compute_student_ids_domain(self):
        for record in self:
            domain = record._get_student_domain()
            students = self.env['res.partner'].search(domain)
            record.student_ids_domain = [(6, 0, students.ids)]

    def _get_student_domain(self):
        self.ensure_one()
        domain = [('course_id', '=', self.feeslip_run_id.fee_struct_id.course_id.id)]
        if self.feeslip_run_id.fee_struct_id.batch_ids:
            batch_domain = [('batch_id', 'in', self.feeslip_run_id.fee_struct_id.batch_ids.ids)]
            domain = expression.AND([domain, batch_domain])
        return domain

    def generate_wizard_lines(self):
        input_types = self.env['oe.feeslip.input.type'].search([])
        wizard_lines = []
        for input_type in input_types:
            wizard_lines.append((0, 0, {
                'input_type_id': input_type.id,
                'amount': 0.0,  # Default amount, can be customized
            }))
        self.wizard_line = wizard_lines

    def compute_sheet(self):
        Feeslip = self.env['oe.feeslip']

        if not self.student_ids:
            raise UserError(_("No students selected. Please select students to generate feeslips."))

        default_values = Feeslip.default_get(Feeslip.fields_get())
        feeslips_vals = []

        success_result = {
            'type': 'ir.actions.act_window',
            'res_model': 'oe.feeslip.run',
            'views': [[False, 'form']],
            'res_id': self.feeslip_run_id.id,
        }
        if not self.student_ids:
            return success_result


        for student in self.student_ids:
            input_lines = [(0, 0, {
                'input_type_id': line.input_type_id.id,
                'amount': line.amount,
            }) for line in self.wizard_line]

            values = dict(default_values, **{
                'name': _('New Feeslip'),
                'student_id': student.id,
                'feeslip_run_id': self.feeslip_run_id.id,
                'date_from': self.feeslip_run_id.date_start,
                'date_to': self.feeslip_run_id.date_end,
                'fee_struct_id': self.feeslip_run_id.fee_struct_id.id,
                'input_line_ids': input_lines,
            })
            feeslips_vals.append(values)

        feeslips = Feeslip.with_context(tracking_disable=True).create(feeslips_vals)
        feeslips._compute_name()
        feeslips.compute_sheet()
        self.feeslip_run_id.state = 'verify'

        return success_result

class FeeslipStudentsLine(models.TransientModel):
    _name = 'oe.feeslip.students.line'
    _description = 'Generate fee variations'

    wizard_id = fields.Many2one('oe.feeslip.students', string="Wizard", ondelete='cascade')
    input_type_id = fields.Many2one('oe.feeslip.input.type', string='Type')
    name = fields.Char(compute='_compute_name')
    amount = fields.Float(string="Amount")

    def _compute_name(self):
        for record in self:
            record.name = record.input_type_id.name
