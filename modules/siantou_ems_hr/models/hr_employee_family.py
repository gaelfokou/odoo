# -*- coding:utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from datetime import date


class EmployeeFamily(models.Model):
    _name = "hr.employee.family"
    _description = "Model pour gérer les enfant d'un employés"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    # name = fields.Char('name')

    employee_id = fields.Many2one('hr.employee', string='Personnel',tracking=True)

    nom_enfant = fields.Char(string="Nom de l'enfant",tracking=True)

    date_naissance = fields.Date(string='Date de naissance',tracking=True)

    age_enfant = fields.Integer(string="Age de l'enfant", readonly=True,compute="_compute_date_naissance")

    genre_enfant = fields.Selection([
        ('girl', 'Feminin'),
        ('boy', 'Masculin')
    ], string='Genre',tracking=True)
    
    school = fields.Boolean('Scolarisé')

    @api.depends("date_naissance")
    def _compute_date_naissance(self):
        for rec in self:
            if rec.date_naissance:
                today = fields.Date.today()
                diff = relativedelta(today, rec.date_naissance)
                rec.age_enfant = diff.years
            else:
                rec.age_enfant = 0