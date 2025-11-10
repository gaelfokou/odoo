# -*- coding:utf-8 -*-

from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

class EmployeeSalaryAllowance(models.Model):
    _name = 'employee.salary.allowance'
    _description = 'Prime sur le salaire'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    allowance_type = fields.Selection([
        ('cd', 'Prime chef de département'),
        ('co', 'Prime coordonnateur'),
    ], string='Type prime', default='cd')
    amount = fields.Float(string='Amount')

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code de la prime doit être unique.'),
    ]
