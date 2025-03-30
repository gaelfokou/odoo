# -*- coding:utf-8 -*-

from odoo import models, fields, api, tools, _

class LeaveType(models.Model):
    _inherit = 'hr.leave.type'

    code = fields.Char(string='Code')

