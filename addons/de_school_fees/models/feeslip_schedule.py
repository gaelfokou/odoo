# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class FeeslipSchedule(models.Model):
    _name = "oe.feeslip.schedule"
    _description = 'Fee Schedule'

    batch_id = fields.Many2one('oe.school.course.batch', string='Batch', required=True)
    course_id = fields.Many2one('oe.school.course', string='Course', related='batch_id.course_id')
    fee_struct_id = fields.Many2one('oe.fee.struct', string='Fee Structure', required=True)
    date = fields.Date(string='Date Due', default=lambda self: fields.Date.today(), required=True)
    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)

    @api.constrains('batch_id', 'course_id', 'fee_struct_id', 'date_from', 'date_to')
    def _check_date_overlap(self):
        for record in self:
            domain = [
                ('batch_id', '=', record.batch_id.id),
                ('course_id', '=', record.course_id.id),
                ('fee_struct_id', '=', record.fee_struct_id.id),
                ('date_from', '<=', record.date_to),
                ('date_to', '>=', record.date_from),
                ('id', '!=', record.id),  # Exclude the current record
            ]
            overlapping_records = self.search(domain)
            if overlapping_records:
                raise ValidationError("Date range overlaps with an existing record.")


    