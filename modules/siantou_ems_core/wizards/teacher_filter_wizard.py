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

TYPE_COUR = {
    'cj': 'Cours du jour',
    'cs': 'Cours du soir',
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

    # Niveau lié à la programmation de cours
    level_id = fields.Many2one(
        'siantou.ems.core.level',
        'Niveau',
    )

    # Filière liée à la programmation de cours
    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        string='Filière',
        related='specialty_id.field_of_study_id',
        store=True
    )

    specialty_id = fields.Many2one(
        'siantou.ems.core.specialty',
        string='Spécialité',
    )

    option_id = fields.Many2one(
        'siantou.ems.core.option',
        string='Option',
    )

    type_cour = fields.Selection([
        ('cj', 'Cours du jour'),
        ('cs', 'Cours du soir'),
    ], string='Type de cours')

    class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe',
    )

    subject_id = fields.Many2one(
        'siantou.ems.core.subject',
        'Cours',
    )

    diplome_availability_id = fields.Many2one(
        'hr.education.diplome.availability',
        string='Diplôme',
    )

    specialty_id_domain = fields.Binary(compute='_compute_school_domain', default=[])

    subject_id_domain = fields.Binary(compute='_compute_class_domain', default=[])

    class_id_domain = fields.Binary(compute='_compute_all_domain', default=[])

    @api.depends('level_id', 'field_of_study_id', 'specialty_id', 'option_id', 'type_cour')
    def _compute_all_domain(self):
        for record in self:
            domain = []
            if record.year_id.id:
                domain.append(('year_id', '=', record.year_id.id))
            if record.level_id.id:
                domain.append(('level_id', '=', record.level_id.id))
            if record.field_of_study_id.id:
                domain.append(('field_of_study_id', '=', record.field_of_study_id.id))
            if record.specialty_id.id:
                domain.append(('specialty_id', '=', record.specialty_id.id))
            if record.option_id.id:
                domain.append(('option_id', '=', record.option_id.id))
            if record.type_cour:
                domain.append(('type_cour', '=', record.type_cour))
            class_ids = []
            classes = self.env['siantou.ems.core.class'].search(domain)
            for classe in classes:
                class_ids.append(classe.id)
            class_ids = list(set(class_ids))
            domain = [
                ('id', 'in', class_ids),
            ]
            record.class_id_domain = domain

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
            record.subject_id = None

    @api.onchange('level_id')
    def _onchange_level(self):
        for record in self:
            record.class_id = None
            record.subject_id = None

    @api.onchange('specialty_id')
    def _onchange_specialty(self):
        for record in self:
            record.class_id = None
            record.option_id = None
            record.subject_id = None

    @api.onchange('option_id')
    def _onchange_option(self):
        for record in self:
            record.class_id = None
            record.subject_id = None

    @api.onchange('type_cour')
    def _onchange_type_cour(self):
        for record in self:
            record.class_id = None
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
            record.subject_id = None

    def action_filter(self):
        domain = []
        title = []
        if self.year_id.id:
            domain.append(('year_id', '=', self.year_id.id))
        if self.school_id.id:
            domain.append(('school_id', '=', self.school_id.id))
            title.append(self.school_id.name)
        if self.level_id.id:
            domain.append(('level_id', '=', self.level_id.id))
            title.append(self.level_id.name)
        if self.field_of_study_id.id:
            domain.append(('field_of_study_id', '=', self.field_of_study_id.id))
            title.append(self.field_of_study_id.name)
        if self.specialty_id.id:
            domain.append(('specialty_id', '=', self.specialty_id.id))
            title.append(self.specialty_id.name)
        if self.option_id.id:
            domain.append(('option_id', '=', self.option_id.id))
            title.append(self.option_id.name)
        if self.type_cour:
            domain.append(('class_id.type_cour', '=', self.type_cour))
            title.append(TYPE_COUR[self.type_cour])
        if self.class_id.id:
            domain.append(('class_id', '=', self.class_id.id))
            title.append(self.class_id.name)
        if self.subject_id.id:
            domain.append(('subject_id', '=', self.subject_id.id))
            title.append(self.subject_id.name)

        employee_ids = []
        timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
        for timetable in timetables:
            employee_ids.append(timetable.employee_id.id)
        employee_ids = list(set(employee_ids))

        domain = [
            ('id', 'in', employee_ids),
            ('is_teacher', '=', True),
        ]

        if len(title) == 0:
            domain = [
                ('is_teacher', '=', True),
            ]

        if self.department_id.id:
            domain.append(('department_id', '=', self.department_id.id))
            title.append(self.department_id.name)

        if self.diplome_availability_id.id:
            domain.append(('diplome_ids', 'in', self.diplome_availability_id.diplome_ids.ids))
            title.append(self.diplome_availability_id.name)

        if len(title) > 0:
            title = '/'.join(title)
        else:
            title = 'Non spécifié'

        self.env['ir.config_parameter'].sudo().set_param(f'filter.{self.env.user.id}', title)

        view_id = self.env.ref('hr.view_employee_tree').id
        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'hr.employee',
            'views': [(view_id, 'tree')],
            'view_id': view_id,
            'domain' : domain,
            'target': 'main',
        }
