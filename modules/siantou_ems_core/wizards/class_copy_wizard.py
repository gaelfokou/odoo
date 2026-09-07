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
TIME_FORMAT = '%H:%M:%S'
TIME_FORMAT_FR = '%H:%M'

STATUS_TIMETABLE = {
    'pending': 'En attente',
    'progress': 'En cours',
    'present': 'Présent',
    'absent': 'Absent',
    'permission': 'Permission',
    'exception': 'Exception',
    'delay': 'Retard',
}

TYPE_COUR = {
    'cj': 'Cours du jour',
    'cs': 'Cours du soir',
}

_logger = logging.getLogger(__name__)


class ClassCopyWizard(models.TransientModel):
    _name = 'class.copy.wizard'
    _description = 'Copie des classes'

    def _default_year(self):
            year = self.env['siantou.ems.core.year'].sudo().search([
                ('active_user_ids', '=', self.env.user.id),
            ], limit=1)
            if not year:
                year = self.env['siantou.ems.core.year'].search([('is_active', '=', True)], limit=1)
            return year

    source_year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année académique source',
        default=_default_year,
        required=True
    )

    destination_year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année académique destination',
        required=True,
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
        related='source_class_id.field_of_study_id'
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
        related='source_class_id.specialty_id'
    )

    option_id = fields.Many2one(
        'siantou.ems.core.option',
        string='Option',
        related='source_class_id.option_id'
    )

    type_cour = fields.Selection([
        ('cj', 'Cours du jour'),
        ('cs', 'Cours du soir'),
    ], string='Type de cours')

    source_class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe source',
    )

    destination_class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe destination',
    )

    source_ue_ids = fields.One2many(
        'siantou.ems.core.unite.enseignement',
        string='Unités d\'enseignement source',
        compute='_compute_source_ues'
    )

    destination_ue_ids = fields.One2many(
        'siantou.ems.core.unite.enseignement',
        string='Unités d\'enseignement destination',
        compute='_compute_destination_ues'
    )

    cycle_id_domain = fields.Binary(compute='_compute_cycle_domain', default=[])

    source_class_id_domain = fields.Binary(compute='_compute_source_class_domain', default=[])

    destination_class_id_domain = fields.Binary(compute='_compute_destination_class_domain', default=[])

    level_id_domain = fields.Binary(compute='_compute_level_domain', default=[])

    @api.depends('cycle_id')
    def _compute_level_domain(self):
        for record in self:
            domain = [
                ('cycle_ids', '=', record.cycle_id.id),
            ]
            record.level_id_domain = domain

    @api.depends('source_year_id', 'school_id', 'level_id', 'cycle_id', 'type_cour')
    def _compute_source_class_domain(self):
        for record in self:
            domain = [
                ('year_id', '=', record.source_year_id.id),
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
            record.source_class_id_domain = domain

    @api.depends('destination_year_id', 'school_id', 'level_id', 'cycle_id', 'type_cour')
    def _compute_destination_class_domain(self):
        for record in self:
            domain = [
                ('year_id', '=', record.destination_year_id.id),
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
            record.destination_class_id_domain = domain

    @api.depends('school_id')
    def _compute_cycle_domain(self):
        for record in self:
            cycle_ids = record.school_id.cycle_ids
            domain = [('id', 'in', cycle_ids.ids)]
            record.cycle_id_domain = domain

    @api.depends('source_class_id')
    def _compute_subject_domain(self):
        for record in self:
            ue_ids = record.source_class_id.ue_ids
            domain = [
                ('ue_ids', 'in', ue_ids.ids)
            ]
            record.subject_id_domain = domain

    @api.onchange('school_id')
    def _onchange_school(self):
        for record in self:
            record.cycle_id = None
            record.level_id = None
            record.source_class_id = None
            record.destination_class_id = None

    @api.onchange('cycle_id')
    def _onchange_cycle(self):
        for record in self:
            record.level_id = None
            record.source_class_id = None
            record.destination_class_id = None

    @api.onchange('level_id')
    def _onchange_level(self):
        for record in self:
            record.source_class_id = None
            record.destination_class_id = None

    @api.onchange('type_cour')
    def _onchange_type_cour(self):
        for record in self:
            record.source_class_id = None
            record.destination_class_id = None

    @api.depends('source_class_id')
    def _compute_source_ues(self):
        # Recherche des emplois du temps qui correspondent à la classe
        for record in self:
            record.source_ue_ids = record.source_class_id.ue_ids

    @api.onchange('source_class_id')
    def _onchange_source_ues(self):
        # Recherche des emplois du temps qui correspondent à la classe
        for record in self:
            record.source_ue_ids = record.source_class_id.ue_ids

    @api.depends('destination_class_id')
    def _compute_destination_ues(self):
        # Recherche des emplois du temps qui correspondent à la classe
        for record in self:
            record.destination_ue_ids = record.destination_class_id.ue_ids

    @api.onchange('destination_class_id')
    def _onchange_destination_ues(self):
        # Recherche des emplois du temps qui correspondent à la classe
        for record in self:
            record.destination_ue_ids = record.destination_class_id.ue_ids

    @api.onchange('school_id')
    def _onchange_school(self):
        for record in self:
            record.level_id = None
            record.source_class_id = None
            record.destination_class_id = None
            record.specialty_id = None
            record.option_id = None
            record.source_ue_ids = []
            record.destination_ue_ids = []

    @api.onchange('level_id')
    def _onchange_level(self):
        for record in self:
            record.source_class_id = None
            record.destination_class_id = None
            record.source_ue_ids = []
            record.destination_ue_ids = []

    @api.onchange('specialty_id')
    def _onchange_specialty(self):
        for record in self:
            record.source_class_id = None
            record.destination_class_id = None
            record.option_id = None
            record.source_ue_ids = []
            record.destination_ue_ids = []

    @api.onchange('option_id')
    def _onchange_option(self):
        for record in self:
            record.source_class_id = None
            record.destination_class_id = None
            record.source_ue_ids = []
            record.destination_ue_ids = []

    @api.onchange('type_cour')
    def _onchange_type_cour(self):
        for record in self:
            record.source_class_id = None
            record.destination_class_id = None
            record.source_ue_ids = []
            record.destination_ue_ids = []

    @api.onchange('source_year_id')
    def _onchange_source_year(self):
        for record in self:
            record.source_class_id = None
            record.source_ue_ids = []

    @api.onchange('destination_year_id')
    def _onchange_destination_year(self):
        for record in self:
            record.destination_class_id = None
            record.destination_ue_ids = []

    def action_copy(self):
        domain = []
        if self.school_id.id:
            domain.append(('school_id', '=', self.school_id.id))
        if self.cycle_id.id:
            domain.append(('cycle_id', '=', self.cycle_id.id))
        if self.level_id.id:
            domain.append(('level_id', '=', self.level_id.id))
        if self.type_cour:
            domain.append(('type_cour', '=', self.type_cour))

        if self.source_class_id.id:
            source_domain = [
                ('id', '=', self.source_class_id.id),
            ]
        else:
            source_domain = [
                ('year_id', '=', self.source_year_id.id),
            ]
            source_domain += domain

        source_class_ids = self.env['siantou.ems.core.class'].search(source_domain)
        source_class_ids = list(source_class_ids)
        for source_class_id in source_class_ids:
            if source_class_id.option_id.id:
                if source_class_id.cycle_id.id == source_class_id.field_of_study_id.cycle_id.id and source_class_id.cycle_id.id == source_class_id.specialty_id.cycle_id.id and source_class_id.cycle_id.id == source_class_id.option_id.cycle_id.id:
                    if source_class_id.field_of_study_id.id == source_class_id.specialty_id.field_of_study_id.id and source_class_id.field_of_study_id.id == source_class_id.option_id.field_of_study_id.id:
                        if source_class_id.specialty_id.id == source_class_id.option_id.specialty_id.id:
                            if self.destination_class_id.id:
                                destination_domain = [
                                    ('id', '=', self.destination_class_id.id),
                                ]
                            else:
                                destination_domain = [
                                    ('year_id', '=', self.destination_year_id.id),
                                    ('school_id', '=', source_class_id.school_id.id),
                                    ('level_id', '=', source_class_id.level_id.id),
                                    ('field_of_study_id', '=', source_class_id.field_of_study_id.id),
                                    ('specialty_id', '=', source_class_id.specialty_id.id),
                                    ('option_id', '=', source_class_id.option_id.id),
                                    ('type_cour', '=', source_class_id.type_cour),
                                ]

                            destination_class_id = self.env['siantou.ems.core.class'].search(destination_domain, limit=1)
                            if not destination_class_id:
                                self.env['siantou.ems.core.class'].create({
                                    'year_id': self.destination_year_id.id,
                                    'school_id': source_class_id.school_id.id,
                                    'level_id': source_class_id.level_id.id,
                                    'field_of_study_id': source_class_id.field_of_study_id.id,
                                    'specialty_id': source_class_id.specialty_id.id,
                                    'option_id': source_class_id.option_id.id,
                                    'type_cour': source_class_id.type_cour,
                                })
            else:
                if source_class_id.cycle_id.id == source_class_id.field_of_study_id.cycle_id.id and source_class_id.cycle_id.id == source_class_id.specialty_id.cycle_id.id:
                    if source_class_id.field_of_study_id.id == source_class_id.specialty_id.field_of_study_id.id:
                        if self.destination_class_id.id:
                            destination_domain = [
                                ('id', '=', self.destination_class_id.id),
                            ]
                        else:
                            destination_domain = [
                                ('year_id', '=', self.destination_year_id.id),
                                ('school_id', '=', source_class_id.school_id.id),
                                ('level_id', '=', source_class_id.level_id.id),
                                ('field_of_study_id', '=', source_class_id.field_of_study_id.id),
                                ('specialty_id', '=', source_class_id.specialty_id.id),
                                ('option_id', '=', False),
                                ('type_cour', '=', source_class_id.type_cour),
                            ]

                        destination_class_id = self.env['siantou.ems.core.class'].search(destination_domain, limit=1)
                        if not destination_class_id:
                            self.env['siantou.ems.core.class'].create({
                                'year_id': self.destination_year_id.id,
                                'school_id': source_class_id.school_id.id,
                                'level_id': source_class_id.level_id.id,
                                'field_of_study_id': source_class_id.field_of_study_id.id,
                                'specialty_id': source_class_id.specialty_id.id,
                                'type_cour': source_class_id.type_cour,
                            })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
