# -*- coding:utf-8 -*-

from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

class EmployeeSalaryDeductionCategory(models.Model):
    _name = 'employee.salary.deduction.category'
    _description = 'Categorie de la retenue sur salaire'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    deduction_ids = fields.One2many(
        'employee.salary.deduction',
        'category_id',
        string='Retenues sur salaire',
    )

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code de la categorie doit être unique.'),
    ]

class EmployeeSalaryDeduction(models.Model):
    _name = 'employee.salary.deduction'
    _description = 'Retenue sur salaire'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    category_id = fields.Many2one('employee.salary.deduction.category', string='Category', required=True)
    deduction_type = fields.Selection([
        ('ir', 'IR (%)'),
        ('cnps', 'CNPS (%)'),
        ('apecus', 'APECUS'),
    ], string='Retenue sur salaire Type', default='ir')
    amount = fields.Float(string='Amount')

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code de la retenue doit être unique.'),
    ]
