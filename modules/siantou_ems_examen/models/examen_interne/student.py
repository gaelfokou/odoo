# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
from odoo.exceptions import UserError, ValidationError

class Student(models.Model):
    _inherit = 'oe.school.student'

    def action_confirm(self):
        for rec in self:
            rec.state = "confirm"


    