# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Department(models.Model):
    _inherit = 'hr.department'

    department_name = fields.Char(
        string='Nom',
        required=True
    )

    name = fields.Char(
        string='Nom du département',
        compute='_compute_name',
        store=True,
    )

    code = fields.Char(
        string='Code',
    )

    school_id = fields.Many2one(
        'siantou.ems.core.school',
        string='École',
        required=True,
    )

    # cycle_id = fields.Many2one(
    #     'oe.school.course',
    #     string='Cursus ou Cycle',
    #     required=True,
    # )

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

    @api.depends('department_name', 'school_id')
    def _compute_name(self):
        for record in self:
            department_name = record.department_name if record.department_name else ''
            school_name = record.school_id.name if record.school_id.id else ''
            name = '{} ({})'.format(department_name, school_name)
            while True:
                if name.find('()') != -1:
                    name = name.replace('()', '')
                else:
                    break
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

    @api.onchange('department_name', 'school_id')
    def _onchange_name(self):
        for record in self:
            record._compute_name()
