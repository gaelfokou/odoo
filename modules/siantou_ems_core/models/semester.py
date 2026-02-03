# -*- coding: utf-8 -*-

import math
from odoo import models, fields, api, tools, _
from datetime import timedelta, datetime, date
from odoo.exceptions import UserError, ValidationError
import re

class Semester(models.Model):
    _name = 'siantou.ems.core.year.semester'
    _description = 'Semestre'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    semester_name = fields.Char(
        string='Nom',
        required=True
    )

    name = fields.Char(string='Nom du semestre',
                       compute='_compute_name', store=True)

    start_time = fields.Date(
        string='Date de début',
        required=True
    )

    end_time = fields.Date(
        string='Date de fin',
        required=True
    )

    year_id = fields.Many2one(
        'siantou.ems.core.year',
        'Année académique',
        help="Année académique à laquelle est lié le semestre",
        required=True,
    )

    # class_ids = fields.One2many(
    #     'siantou.ems.core.class',
    #     'semestre_id',
    #     string='Classes',
    #     help="classe à laquelle est lié le semestre",
    #     required=True
    # )

    number_of_week = fields.Integer(
        'Nombre de semaines',
        compute='_compute_number_of_week',
        help='Nombre de semaines sur le semestre',
        store=True
    )

    ue_ids = fields.Many2many('siantou.ems.core.unite.enseignement', 'semester_ue_rel', 'semester_id', 'ue_id', string='Unités d\'enseignement')

    class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe',
    )

    level_ids = fields.Many2many(
        'siantou.ems.core.level',
        'semester_level_rel',
        'semester_id',
        'level_id',
        string='Niveaux',
    )

    # _sql_constraints = [
    #     ('unique_name', 'unique(name)', 'Le nom du semestre doit être unique.'),
    # ]

    @api.depends('semester_name', 'year_id')
    def _compute_name(self):
        for record in self:
            semester_name = record.semester_name if record.semester_name else ''
            year_name = record.year_id.name if record.year_id.id else ''
            name = '{} ({})'.format(semester_name, year_name)
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

    @api.onchange('semester_name', 'year_id')
    def _onchange_name(self):
        for record in self:
            semester_name = record.semester_name if record.semester_name else ''
            year_name = record.year_id.name if record.year_id.id else ''
            name = '{} ({})'.format(semester_name, year_name)
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

    # @api.constrains('start_time', 'end_time')
    # def _check_date_overlap(self):
    #     for record in self:
    #         semesters = self.env['siantou.ems.core.year.semester'].search([('id', '!=', record.id)]).filtered(lambda rec: not (rec.start_time >= record.end_time or rec.end_time <= record.start_time))
    #         semesters = list(semesters)
    #         if len(semesters) > 0:
    #             raise ValidationError('Les semestres ne peuvent se supperposer')

    @api.constrains('start_time', 'end_time')
    def _constrains_date(self):
        for record in self:
            if record.start_time >= record.end_time:
                raise ValidationError('La date de fin doit être supérieure à la date de début')

    @api.onchange('start_time', 'end_time')
    def _onchange_number_of_week(self):
        for record in self:
            if record.start_time and record.end_time:
                start_time = record.start_time
                end_time = record.end_time
                diff_days = (end_time - start_time).days
                record.number_of_week = math.ceil(diff_days / 7)
            else:
                record.number_of_week = 0

    @api.depends('start_time', 'end_time')
    def _compute_number_of_week(self):
        for record in self:
            if record.start_time and record.end_time:
                start_time = record.start_time
                end_time = record.end_time
                diff_days = (end_time - start_time).days
                record.number_of_week = math.ceil(diff_days / 7)
            else:
                record.number_of_week = 0
