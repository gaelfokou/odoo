# -*- coding:utf-8 -*-

from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval


class EmployeeSalaryDeduction(models.Model):
    _name = 'employee.salary.deduction'
    _description = 'Retenue sur le salaire'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    deduction_type = fields.Selection([
        ('ir', 'IR (%)'),
        ('cnps', 'CNPS (%)'),
        ('apecus', 'APECUS'),
    ], string='Type retenue', default='ir')
    amount = fields.Float(string='Amount')

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code de la retenue doit être unique.'),
    ]
