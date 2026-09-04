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
        string='Année académique',
    )

    school_id = fields.Many2one(
        'siantou.ems.core.school',
        string='École',
        required=True,
    )

    level_id = fields.Many2one(
        'siantou.ems.core.level',
        string='Niveau',
    )

    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        string='Filière',
        related='class_id.field_of_study_id'
    )

    cycle_id = fields.Many2one(
        'oe.school.course',
        string='Cursus ou Cycle',
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Département',
        related='specialty_id.department_id'
    )

    specialty_id = fields.Many2one(
        'siantou.ems.core.specialty',
        string='Spécialité',
        related='class_id.specialty_id'
    )

    option_id = fields.Many2one(
        'siantou.ems.core.option',
        string='Option',
        related='class_id.option_id'
    )

    type_cour = fields.Selection([
            ('cj', 'Cours du jour'),
            ('cs', 'Cours du soir'),
        ], string='Type de cours',
    )

    class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe',
    )

    semester_id = fields.Many2one(
        'siantou.ems.core.year.semester',
        string='Semestre',
    )

    cycle_id_domain = fields.Binary(compute='_compute_cycle_domain', default=[])

    class_id_domain = fields.Binary(compute='_compute_class_domain', default=[])

    level_id_domain = fields.Binary(compute='_compute_level_domain', default=[])

    @api.depends('cycle_id')
    def _compute_level_domain(self):
        for record in self:
            domain = [
                ('cycle_ids', '=', record.cycle_id.id),
            ]
            record.level_id_domain = domain

    @api.depends('year_id', 'school_id', 'level_id', 'cycle_id', 'type_cour')
    def _compute_class_domain(self):
        for record in self:
            domain = [
                ('year_id', '=', record.year_id.id),
                ('school_id', '=', record.school_id.id),
                ('level_id', '=', record.level_id.id),
                ('cycle_id', '=', record.cycle_id.id)
            ]
            if record.type_cour:
                domain.append(('type_cour', '=', record.type_cour))
            classes = self.env['siantou.ems.core.class'].search(domain)
            domain = [
                ('id', 'in', classes.ids),
            ]
            record.class_id_domain = domain

    @api.depends('school_id')
    def _compute_cycle_domain(self):
        for record in self:
            cycle_ids = record.school_id.cycle_ids
            domain = [('id', 'in', cycle_ids.ids)]
            record.cycle_id_domain = domain

    @api.onchange('year_id')
    def _onchange_year(self):
        for record in self:
            record.school_id = None
            record.cycle_id = None
            record.level_id = None
            record.class_id = None

    @api.onchange('school_id')
    def _onchange_school(self):
        for record in self:
            record.cycle_id = None
            record.level_id = None
            record.class_id = None

    @api.onchange('cycle_id')
    def _onchange_cycle(self):
        for record in self:
            record.level_id = None
            record.class_id = None

    @api.onchange('level_id')
    def _onchange_level(self):
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
            title.append(self.year_id.name)
        if self.school_id.id:
            domain.append(('school_id', '=', self.school_id.id))
            title.append(self.school_id.name)
        if self.cycle_id.id:
            domain.append(('cycle_id', '=', self.cycle_id.id))
            title.append(self.cycle_id.name)
        if self.level_id.id:
            domain.append(('level_id', '=', self.level_id.id))
            title.append(self.level_id.name)
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
                classe_ue_ids = classe_ue_ids.filtered(lambda rec: semester_id in rec.semester_ids.ids)
            for ue_id in classe_ue_ids:
                ue_ids.append(ue_id.id)
        ue_ids = list(set(ue_ids))

        domain = [
            ('ue_ids', 'in', ue_ids),
        ]

        if len(title) > 0:
            title = ' / '.join(title)
        else:
            title = 'Non spécifié'

        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', title)

        view_id = self.env.ref('siantou_ems_core.subject_tree_view').id
        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'siantou.ems.core.subject',
            'views': [(view_id, 'tree'), (False, 'form')],
            'view_id': view_id,
            'domain': domain,
            'target': 'main',
        }
