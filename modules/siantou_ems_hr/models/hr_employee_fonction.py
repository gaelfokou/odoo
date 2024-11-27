# -*- coding: utf-8 -*-

from odoo import models, fields, api

class HrEmployeeFonction(models.Model):
    _name = "hr.employee.fonction"
    _description = "Fonction des personnels"
    
    name = fields.Char(
        string='Libellé',
        size=200,
        required=True)
    
    code = fields.Char(
        string='Code',
        size=10)
    
    active = fields.Boolean(
        string='Active ?',
        default=True)

    rang = fields.Many2one("hr.employee.rang", string="Rang")
    
    is_manager = fields.Boolean('Est un responsable ?', default=False)
    
    