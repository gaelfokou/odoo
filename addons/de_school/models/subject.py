# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError
from random import randint


class SchoolCourseSubjectGroup(models.Model):
    _name = 'oe.school.subject.group'
    _description = 'Filières'
    
    name = fields.Char(string='Filière', required=True, index=True, translate=True)


class SchoolCourseSubject(models.Model):
    _name = 'oe.school.subject'
    _description = 'Cours'
    
    def _default_color(self):
        return randint(1, 11)
    
    name = fields.Char(string='Cours', required=True, index=True, translate=True)
    code = fields.Char(string='Code', required=True, size=10)
    active = fields.Boolean('Actif', default=True)
    subject_group_id = fields.Many2one('oe.school.subject.group', string='Filière')
    color = fields.Integer(default=_default_color)
    company_id = fields.Many2one('res.company', 'Université', index=True)

    
