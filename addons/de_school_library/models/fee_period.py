# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, _lt
from odoo.tools import get_timedelta
from odoo.tools import float_compare, float_is_zero


class FeePeriod(models.Model):
    _name = 'oe.library.fees.period'
    _description = 'Fee Period'
    _order = 'unit,duration'

    active = fields.Boolean(default=True)
    name = fields.Char(compute='_compute_name', store=True, readonly=False)
    duration = fields.Integer(string="Duration", required=True, default=1,
                              help="Minimum duration before this rule is applied. If set to 0, it represents a fixed temporal price.")
    unit = fields.Selection([('day', 'Days'), ("week", "Weeks"), ("month", "Months"), ('year', 'Years')],
        string="Unit", required=True, default='month')
    duration_display = fields.Char(compute='_compute_duration_display')
    subscription_unit_display = fields.Char(compute='_compute_subscription_unit_display')

    _sql_constraints = [
        ('temporal_recurrence_duration', "CHECK(duration >= 0)", "The pricing duration has to be greater or equal to 0."),
    ]
