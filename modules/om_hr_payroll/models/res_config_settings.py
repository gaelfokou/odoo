# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_om_hr_payroll_account = fields.Boolean(string='Payroll Accounting ?')

