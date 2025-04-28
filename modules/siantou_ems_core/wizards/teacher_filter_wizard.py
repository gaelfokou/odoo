from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from pprint import pformat
import pandas as pd
import numpy as np
import re
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import copy
import logging

DATE_FORMAT = '%Y-%m-%d'
DATE_FORMAT_FR = '%d/%m/%Y'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATETIME_FORMAT_FR = '%d/%m/%Y %H:%M'
TIME_FORMAT = '%H:%M'

CURRENT_WEEKDAY = {
    0: 'Lundi',
    1: 'Mardi',
    2: 'Mercredi',
    3: 'Jeudi',
    4: 'Vendredi',
    5: 'Samedi',
    6: 'Dimanche',
}

STATUS_TIMETABLE = {
    '0': 'En attente',
    '1': 'Présent',
    '2': 'Absent',
    '3': 'Permissionnaire',
    '4': 'Exception',
}

_logger = logging.getLogger(__name__)

class TeacherFilterWizard(models.TransientModel):
    _name = 'teacher.filter.wizard'
    _description = 'Filtre des emplois du temps'

    year_id = fields.Many2one(
        'siantou.ems.core.year',
        'Année académique',
    )

    # Ajouter un champ de relation vers hr.department pour lier la filière au département
    department_id = fields.Many2one(
        'hr.department',
        string='Département'
    )

    school_id = fields.Many2one(
        'siantou.ems.core.school',
        string='Ecole',
    )

    # Filière liée à la programmation de cours
    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        string='Filière',
        related='specialty_id.field_of_study_id',
        store=True
    )

    # Niveau lié à la programmation de cours
    level_id = fields.Many2one(
        'siantou.ems.core.level',
        'Niveau',
    )

    class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe',
    )

    specialty_id = fields.Many2one(
        'siantou.ems.core.specialty',
        string='Spécialité',
    )

    option_id = fields.Many2one(
        'siantou.ems.core.option',
        string='Option',
    )

    ue_id = fields.Many2one(
        'siantou.ems.core.unite.enseignement',
        string='Unité d\'enseignement',
    )

    subject_id = fields.Many2one(
        'siantou.ems.core.subject',
        string='Cours',
    )

    specialty_id_domain = fields.Binary(compute='_compute_school_domain', default=[])

    subject_id_domain = fields.Binary(compute='_compute_class_domain', default=[])

    department_id = fields.Many2one(
        'hr.department',
        string='Département'
    )

    @api.depends('school_id')
    def _compute_school_domain(self):
        for record in self:
            domain = []
            if record.school_id.id:
                field_of_study_ids = self.env['siantou.ems.core.field_of_study'].search([('school_id', '=', record.school_id.id)])
                domain = [('field_of_study_id', 'in', field_of_study_ids.ids)]
            record.specialty_id_domain = domain

    @api.onchange('school_id')
    def _onchange_school(self):
        for record in self:
            record.field_of_study_id = None
            record.level_id = None
            record.class_id = None
            record.specialty_id = None
            record.option_id = None
            record.ue_id = None
            record.subject_id = None

    # @api.onchange('field_of_study_id')
    # def _onchange_field_of_study(self):
    #     for record in self:
    #         record.level_id = None
    #         record.class_id = None
    #         record.specialty_id = None
    #         record.option_id = None
    #         record.ue_id = None
    #         record.subject_id = None

    @api.onchange('level_id')
    def _onchange_level(self):
        for record in self:
            record.class_id = None
            record.ue_id = None
            record.subject_id = None

    @api.onchange('specialty_id')
    def _onchange_specialty(self):
        for record in self:
            record.class_id = None
            record.option_id = None
            record.ue_id = None
            record.subject_id = None

    @api.onchange('option_id')
    def _onchange_option(self):
        for record in self:
            record.class_id = None
            record.ue_id = None
            record.subject_id = None

    @api.depends('class_id')
    def _compute_class_domain(self):
        for record in self:
            domain = []
            if record.class_id.id:
                ue_ids = record.class_id.ue_ids
                domain = [('ue_ids', 'in', ue_ids.ids)]
            record.subject_id_domain = domain

    @api.onchange('class_id')
    def _onchange_class(self):
        for record in self:
            record.ue_id = None
            record.subject_id = None

    def action_teacher_filter(self):
        domain = []
        if self.year_id.id:
            domain.append(('year_id', '=', self.year_id.id))
        if self.school_id.id:
            domain.append(('school_id', '=', self.school_id.id))
        if self.field_of_study_id.id:
            domain.append(('field_of_study_id', '=', self.field_of_study_id.id))
        if self.level_id.id:
            domain.append(('level_id', '=', self.level_id.id))
        if self.class_id.id:
            domain.append(('id', '=', self.class_id.id))
        if self.specialty_id.id:
            domain.append(('specialty_id', '=', self.specialty_id.id))
        if self.option_id.id:
            domain.append(('option_id', '=', self.option_id.id))
        if self.ue_id.id:
            domain.append(('ue_ids', '=', self.ue_id.id))

        ue_ids = []
        classes = self.env['siantou.ems.core.class'].search(domain)
        for classe in classes:
            ue_ids += classe.ue_ids.ids
        ue_ids = list(set(ue_ids))

        domain = [
            ('ue_ids', 'in', ue_ids),
        ]

        if self.subject_id.id:
            domain.append(('id', '=', self.subject_id.id))

        subjects = self.env['siantou.ems.core.subject'].search(domain)
        subject_ids = subjects.ids

        domain = [
            ('subject_ids', 'in', subject_ids),
            ('is_teacher', '=', True),
        ]

        if self.department_id.id:
            domain.append(('department_id', '=', self.department_id.id))

        action = self.env.ref('siantou_ems_core.action_hr_employees_teachers').read()[0]
        action.update({
            'name': 'Enseignants',
            'res_model': 'hr.employee',
            'type': 'ir.actions.act_window',
            'domain' : domain,
            'context': {'no_breadcrumbs': True},
        })
        return action
