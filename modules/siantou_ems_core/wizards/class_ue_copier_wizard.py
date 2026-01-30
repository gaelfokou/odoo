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

class ClassUeCopierWizard(models.TransientModel):
    _name = 'class.ue.copier.wizard'
    _description = 'Copieur des unités d\'enseignement'

    source_year_id = fields.Many2one(
        'siantou.ems.core.year',
        'Année académique source',
        required=True,
    )

    destination_year_id = fields.Many2one(
        'siantou.ems.core.year',
        'Année académique destination',
        required=True,
    )

    school_id = fields.Many2one(
        'siantou.ems.core.school',
        string='École',
        required=True,
    )

    level_id = fields.Many2one(
        'siantou.ems.core.level',
        'Niveau',
        required=True,
    )

    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        string='Filière',
        related='specialty_id.field_of_study_id',
        store=True
    )

    specialty_id = fields.Many2one(
        'siantou.ems.core.specialty',
        string='Spécialité',
        required=True,
    )

    option_id = fields.Many2one(
        'siantou.ems.core.option',
        string='Option',
    )

    type_cour = fields.Selection([
        ('cj', 'Cours du jour'),
        ('cs', 'Cours du soir'),
    ], string='Type de cours')

    source_class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe source',
        required=True,
    )

    destination_class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe destination',
        required=True,
    )

    source_ue_ids = fields.One2many(
        'siantou.ems.core.unite.enseignement',
        string='Unités d\'enseignement source',
        compute='_compute_source_ues',
        store=False
    )

    destination_ue_ids = fields.One2many(
        'siantou.ems.core.unite.enseignement',
        string='Unités d\'enseignement destination',
        compute='_compute_destination_ues',
        store=False
    )

    specialty_id_domain = fields.Binary(compute='_compute_school_domain', default=[])

    source_class_id_domain = fields.Binary(compute='_compute_all_source_domain', default=[])

    destination_class_id_domain = fields.Binary(compute='_compute_all_destination_domain', default=[])

    @api.depends('source_class_id')
    def _compute_source_ues(self):
        # Recherche des emplois du temps qui correspondent à la classe
        for record in self:
            record.source_ue_ids = record.source_class_id.ue_ids

    @api.depends('destination_class_id')
    def _compute_destination_ues(self):
        # Recherche des emplois du temps qui correspondent à la classe
        for record in self:
            record.destination_ue_ids = record.destination_class_id.ue_ids

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

    @api.depends('source_year_id', 'level_id', 'field_of_study_id', 'specialty_id', 'option_id', 'type_cour')
    def _compute_all_source_domain(self):
        for record in self:
            domain = []
            if record.source_year_id.id:
                domain.append(('year_id', '=', record.source_year_id.id))
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
            record.source_class_id_domain = domain

    @api.depends('destination_year_id', 'level_id', 'field_of_study_id', 'specialty_id', 'option_id', 'type_cour')
    def _compute_all_destination_domain(self):
        for record in self:
            domain = []
            if record.destination_year_id.id:
                domain.append(('year_id', '=', record.destination_year_id.id))
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
            record.destination_class_id_domain = domain

    @api.onchange('school_id')
    def _onchange_school(self):
        for record in self:
            record.field_of_study_id = None
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

    def action_copier(self):
        source_class_id = self.env['siantou.ems.core.class'].search([('id', '=', self.source_class_id.id)], limit=1)
        destination_class_id = self.env['siantou.ems.core.class'].search([('id', '=', self.destination_class_id.id)], limit=1)

        for group_id in source_class_id.group_ids:
            destination_class_id.group_ids.create({
                'name': group_id.name,
                'class_id': destination_class_id.id,
            })

        ue_ids = []
        for ue_id in source_class_id.ue_ids:
            destination_semester_ids = []
            for source_semester_id in ue_id.semester_ids:
                years = source_semester_id.year_id.name.split('-')
                years = [int(y) for y in years]
                new_years = self.destination_year_id.name.split('-')
                new_years = [int(y) for y in new_years]

                destination_semester_id = self.env['siantou.ems.core.year.semester'].search([
                    ('semester_name', '=', source_semester_id.semester_name),
                    ('year_id', '=', self.destination_year_id.id),
                ], limit=1)
                if not destination_semester_id:
                    year, week, day = source_semester_id.start_time.isocalendar()
                    try:
                        index_year = years.index(year)
                    except ValueError:
                        index_year = -1
                    if index_year != -1 and len(years) > 1 and len(new_years) > 1:
                        year = new_years[index_year]
                    start_time = date.fromisocalendar(year, week, day)

                    year, week, day = source_semester_id.end_time.isocalendar()
                    try:
                        index_year = years.index(year)
                    except ValueError:
                        index_year = -1
                    if index_year != -1 and len(years) > 1 and len(new_years) > 1:
                        year = new_years[index_year]
                    end_time = date.fromisocalendar(year, week, day)

                    destination_semester_id = self.env['siantou.ems.core.year.semester'].create({
                        'name': source_semester_id.name,
                        'start_time': start_time,
                        'end_time': end_time,
                        'year_id': self.destination_year_id.id,
                    })
                    level_ids = [(4, level_id.id) for level_id in source_semester_id.level_ids]
                    # destination_semester_id.level_ids = level_ids
                    destination_semester_id.write({'level_ids': level_ids })

                destination_semester_ids.append(destination_semester_id)

            ue = self.env['siantou.ems.core.unite.enseignement'].search([
                ('code', '=', ue_id.code),
                ('semester_ids', 'in', [semester_id.id for semester_id in destination_semester_ids]),
            ], limit=1)
            if not ue:
                ue = self.env['siantou.ems.core.unite.enseignement'].create({
                    'code': ue_id.code,
                    'name': ue_id.name,
                    'type_ue': ue_id.type_ue,
                })
                semester_ids = [(4, semester_id.id) for semester_id in destination_semester_ids]
                subject_ids = [(4, subject_id.id) for subject_id in ue_id.subject_ids]
                ue.write({
                    'semester_ids': semester_ids,
                    'subject_ids': subject_ids,
                })
                for syllabus_id in ue_id.syllabus_ids:
                    self.env['siantou.ems.core.syllabus'].create({
                        'name': syllabus_id.name,
                        'ue_id': ue.id,
                        'subject_id': syllabus_id.subject_id.id,
                        'class_id': destination_class_id.id,
                        'description': syllabus_id.description,
                        'pourcentage_cc': syllabus_id.pourcentage_cc,
                        'pourcentage_exam': syllabus_id.pourcentage_exam,
                        'pourcentage_presence': syllabus_id.pourcentage_presence,
                        'note_sn': syllabus_id.note_sn,
                        'coefficient': syllabus_id.coefficient,
                        'note_sn': syllabus_id.note_sn,
                        'cm': syllabus_id.cm,
                        'tp': syllabus_id.tp,
                        'td': syllabus_id.td,
                        'te': syllabus_id.te,
                        # 'pro_pe_id': syllabus_id.pro_pe_id,
                    })
            ue_ids.append(ue)
        ue_ids = [(4, ue_id.id) for ue_id in ue_ids]
        destination_class_id.write({'ue_ids': ue_ids })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
