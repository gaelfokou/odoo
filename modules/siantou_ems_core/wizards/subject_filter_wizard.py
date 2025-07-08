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

STATUS_CLASS = {
    'timetable_available': 'Emplois du temps disponibles',
    'timetable_not_available': 'Emplois du temps pas disponibles',
    'student_available': 'Étudiants disponibles',
    'student_not_available': 'Étudiants pas disponibles',
    'student_more_than_or_equal': 'Étudiants plus de ou égal à',
    'student_less_than': 'Étudiants moins de',
}

_logger = logging.getLogger(__name__)

class SubjectFilterWizard(models.TransientModel):
    _name = 'subject.filter.wizard'
    _description = 'Filtre des subjects'

    year_id = fields.Many2one(
        'siantou.ems.core.year',
        'Année académique',
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

    semester_id = fields.Many2one(
        'siantou.ems.core.year.semester',
        string='Semestre',
    )

    specialty_id_domain = fields.Binary(compute='_compute_school_domain', default=[])

    @api.depends('school_id')
    def _compute_school_domain(self):
        for record in self:
            domain = []
            if record.school_id.id:
                field_of_study_ids = self.env['siantou.ems.core.field_of_study'].search([('school_id', '=', record.school_id.id)])
                domain = [
                    ('field_of_study_id', 'in', field_of_study_ids.ids)
                ]
            record.specialty_id_domain = domain

    @api.onchange('school_id')
    def _onchange_school(self):
        for record in self:
            record.field_of_study_id = None
            record.level_id = None
            record.specialty_id = None
            record.option_id = None
            record.class_id = None

    @api.onchange('specialty_id')
    def _onchange_specialty(self):
        for record in self:
            record.option_id = None
            record.class_id = None

    @api.onchange('option_id')
    def _onchange_option(self):
        for record in self:
            record.class_id = None

    @api.onchange('type_cour')
    def _onchange_type_cour(self):
        for record in self:
            record.class_id = None

    def action_filter(self):
        domain = []
        title = []
        if self.year_id.id:
            domain.append(('year_id', '=', self.year_id.id))
        if self.school_id.id:
            domain.append(('school_id', '=', self.school_id.id))
            title.append(self.school_id.name)
        if self.field_of_study_id.id:
            domain.append(('field_of_study_id', '=', self.field_of_study_id.id))
            title.append(self.field_of_study_id.name)
        if self.level_id.id:
            domain.append(('level_id', '=', self.level_id.id))
            title.append(self.level_id.name)
        if self.specialty_id.id:
            domain.append(('specialty_id', '=', self.specialty_id.id))
            title.append(self.specialty_id.name)
        if self.option_id.id:
            domain.append(('option_id', '=', self.option_id.id))
            title.append(self.option_id.name)
        if self.type_cour:
            domain.append(('type_cour', '=', self.type_cour))
            title.append(TYPE_COUR[self.type_cour])
        if self.class_id.id:
            domain.append(('id', '=', self.class_id.id))
            title.append(self.class_id.name)
        semester_id = None
        if self.semester_id.id:
            semester_id = self.semester_id.id
            title.append(self.semester_id.name)

        ue_ids = []
        classes = self.env['siantou.ems.core.class'].search(domain)
        for classe in classes:
            classe_ue_ids = classe.ue_ids
            if semester_id:
                classe_ue_ids = classe_ue_ids.filtered(lambda rec: rec.semestre_id.id == semester_id)
            for ue_id in classe_ue_ids:
                ue_ids.append(ue_id.id)
        ue_ids = list(set(ue_ids))

        domain = [
            ('ue_ids', 'in', ue_ids),
        ]

        if len(title) > 0:
            title = '/'.join(title)
        else:
            title = 'Non spécifié'

        self.env['ir.config_parameter'].sudo().set_param(f'filter.{self.env.user.id}', title)

        view_id = self.env.ref('siantou_ems_core.subject_tree_view').id
        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'siantou.ems.core.subject',
            'views': [(view_id, 'tree'), (False, 'form')],
            'view_id': view_id,
            'domain' : domain,
            'target': 'main',
        }
