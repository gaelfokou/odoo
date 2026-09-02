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


class StudentFilterWizard(models.TransientModel):
    _name = 'student.filter.wizard'
    _description = 'Filtre des étudiants'

    year_id = fields.Many2one(
        'siantou.ems.core.year',
        'Année académique',
    )

    school_id = fields.Many2one(
        'siantou.ems.core.school',
        string='École',
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

        student_ids = []
        classes = self.env['siantou.ems.core.class'].search(domain)
        for classe in classes:
            student_ids += classe.student_ids.ids
        student_ids = list(set(student_ids))

        domain = [
            ('id', 'in', student_ids),
        ]

        if len(title) > 0:
            title = ' / '.join(title)
        else:
            title = 'Non spécifié'

        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', title)

        view_id = self.env.ref('student_tree_view').id
        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'oe.school.student',
            'views': [(view_id, 'tree'), (False, 'form')],
            'view_id': view_id,
            'domain': domain,
            'target': 'main',
        }
