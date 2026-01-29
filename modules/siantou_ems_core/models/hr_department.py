# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Department(models.Model):
    _inherit = 'hr.department'

    code = fields.Char(
        string='Code',
    )

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

    group_ids = fields.Many2many('siantou.ems.timetable.group', 'department_group_rel', 'department_id', 'group_id', string="Versions d'emploi du temps")

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code du département doit être unique.'),
    ]
