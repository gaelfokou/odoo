# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import math

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
    semester_id = fields.One2many('oe.school.year.semester', 'subject_ids', string='Semestre')
    credit_hour = fields.Integer(string="Volume horaire")
    duration_per_week = fields.Integer(string="Durée du cours", compute='_compute_duration_per_week', store=True)
    priority = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
    ], string='Priority')
    shared_subject = fields.Boolean(string="Tronc commun", default=False)

    def _compute_duration_per_week(self):
        credit_hour = self.credit_hour
        weeks_on_semester = self.semester_id.number_of_week

        return math.ceil(credit_hour/weeks_on_semester)
