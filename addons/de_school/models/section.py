# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError

class SchoolSection(models.Model):
    _name = 'oe.school.course.section'
    _description = 'Sections du cursus'
    _rec_name = 'display_name'
    
    name = fields.Char(string='Section du cursus', required=True, index=True, translate=True)
    course_id = fields.Many2one('oe.school.course', string='Cursus', required=True)
    display_name = fields.Char(string="Nom d'affichage", compute='_compute_display_name')

    @api.depends('name','course_id.code')
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.course_id.code + '/' + record.name
