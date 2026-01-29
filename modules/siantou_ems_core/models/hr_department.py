# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Department(models.Model):
    _inherit = 'hr.department'

    school_id = fields.Many2one(
        'siantou.ems.core.school',
        string='École',
    )

    field_of_study_ids = fields.One2many(
        'siantou.ems.core.field_of_study',
        'department_id',
        string='Filières'
    )

    specialty_ids = fields.One2many(
        'siantou.ems.core.specialty',
        'department_id',
        string='Spécialités'
    )

    code = fields.Char(
        string='Code',
    )

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code du département doit être unique.'),
    ]
