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

class TimetableCopyWizard(models.TransientModel):
    _name = 'timetable.copy.wizard'
    _description = 'Copie des emplois du temps'

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

    semester_id = fields.Many2one(
        'siantou.ems.core.year.semester',
        string='Semestre',
        related='group_id.semester_id',
        store=False
    )

    group_id = fields.Many2one(
        'siantou.ems.timetable.group',
        string='Version d\'emploi du temps',
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
        store=False
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

    source_timetable_ids = fields.One2many(
        'siantou.ems.timetable.timetable',
        string='Emplois du temps source',
        compute='_compute_source_timetables',
        store=False
    )

    destination_timetable_ids = fields.One2many(
        'siantou.ems.timetable.timetable',
        string='Emplois du temps destination',
        compute='_compute_destination_timetables',
        store=False
    )

    subject_id = fields.Many2one(
        'siantou.ems.core.subject',
        string='Cours',
    )

    specialty_id_domain = fields.Binary(compute='_compute_school_domain', default=[])

    source_class_id_domain = fields.Binary(compute='_compute_all_source_domain', default=[])

    destination_class_id_domain = fields.Binary(compute='_compute_all_destination_domain', default=[])

    subject_id_domain = fields.Binary(compute='_compute_class_domain', default=[])

    school_id_domain = fields.Binary(compute='_compute_group_domain', default=[])

    level_id_domain = fields.Binary(compute='_compute_semester_domain', default=[])

    @api.depends('semester_id')
    def _compute_semester_domain(self):
        for record in self:
            domain = []
            if record.semester_id.id:
                domain = [
                    ('semester_ids', '=', record.semester_id.id)
                ]
            record.level_id_domain = domain

    @api.depends('group_id')
    def _compute_group_domain(self):
        for record in self:
            domain = []
            if record.group_id.id:
                domain = [
                    ('id', 'in', record.group_id.school_ids.ids)
                ]
            record.school_id_domain = domain

    @api.depends('group_id', 'school_id')
    def _compute_school_domain(self):
        for record in self:
            domain = []
            if record.school_id.id:
                domain.append(('school_id', '=', record.school_id.id))
            record.specialty_id_domain = domain

    @api.depends('source_class_id', 'semester_id')
    def _compute_class_domain(self):
        for record in self:
            domain = []
            if record.source_class_id.id:
                ue_ids = record.source_class_id.ue_ids
                if record.semester_id.id:
                    ue_ids = ue_ids.filtered(lambda rec: record.semester_id.id in rec.semester_ids.ids)
                domain = [
                    ('ue_ids', 'in', ue_ids.ids)
                ]
            record.subject_id_domain = domain

    @api.depends('source_class_id', 'semester_id', 'subject_id')
    def _compute_source_timetables(self):
        # Recherche des emplois du temps qui correspondent à la classe
        for record in self:
            timetable_ids = self.env['siantou.ems.timetable.timetable'].search([('class_id', '=', record.source_class_id.id)])
            if record.semester_id.id:
                timetable_ids = timetable_ids.filtered(lambda rec: rec.semester_id.id == record.semester_id.id)
            if record.subject_id.id:
                timetable_ids = timetable_ids.filtered(lambda rec: rec.subject_id.id == record.subject_id.id)
            record.source_timetable_ids = timetable_ids

    @api.onchange('source_class_id', 'semester_id', 'subject_id')
    def _onchange_source_timetables(self):
        # Recherche des emplois du temps qui correspondent à la classe
        for record in self:
            timetable_ids = self.env['siantou.ems.timetable.timetable'].search([('class_id', '=', record.source_class_id.id)])
            if record.semester_id.id:
                timetable_ids = timetable_ids.filtered(lambda rec: rec.semester_id.id == record.semester_id.id)
            if record.subject_id.id:
                timetable_ids = timetable_ids.filtered(lambda rec: rec.subject_id.id == record.subject_id.id)
            record.source_timetable_ids = timetable_ids

    @api.depends('destination_class_id', 'semester_id', 'subject_id')
    def _compute_destination_timetables(self):
        # Recherche des emplois du temps qui correspondent à la classe
        for record in self:
            timetable_ids = self.env['siantou.ems.timetable.timetable'].search([('class_id', '=', record.destination_class_id.id)])
            if record.semester_id.id:
                timetable_ids = timetable_ids.filtered(lambda rec: rec.semester_id.id == record.semester_id.id)
            if record.subject_id.id:
                timetable_ids = timetable_ids.filtered(lambda rec: rec.subject_id.id == record.subject_id.id)
            record.destination_timetable_ids = timetable_ids

    @api.onchange('destination_class_id', 'semester_id', 'subject_id')
    def _onchange_destination_timetables(self):
        # Recherche des emplois du temps qui correspondent à la classe
        for record in self:
            timetable_ids = self.env['siantou.ems.timetable.timetable'].search([('class_id', '=', record.destination_class_id.id)])
            if record.semester_id.id:
                timetable_ids = timetable_ids.filtered(lambda rec: rec.semester_id.id == record.semester_id.id)
            if record.subject_id.id:
                timetable_ids = timetable_ids.filtered(lambda rec: rec.subject_id.id == record.subject_id.id)
            record.destination_timetable_ids = timetable_ids

    @api.depends('source_year_id', 'level_id', 'school_id', 'specialty_id', 'option_id', 'type_cour')
    def _compute_all_source_domain(self):
        for record in self:
            domain = []
            if record.source_year_id.id:
                domain.append(('year_id', '=', record.source_year_id.id))
            if record.school_id.id:
                domain.append(('school_id', '=', record.school_id.id))
            if record.level_id.id:
                domain.append(('level_id', '=', record.level_id.id))
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

    @api.depends('destination_year_id', 'level_id', 'school_id', 'specialty_id', 'option_id', 'type_cour')
    def _compute_all_destination_domain(self):
        for record in self:
            domain = []
            if record.destination_year_id.id:
                domain.append(('year_id', '=', record.destination_year_id.id))
            if record.school_id.id:
                domain.append(('school_id', '=', record.school_id.id))
            if record.level_id.id:
                domain.append(('level_id', '=', record.level_id.id))
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

    @api.onchange('group_id')
    def _onchange_group(self):
        for record in self:
            record.school_id = None
            record.level_id = None
            record.source_class_id = None
            record.destination_class_id = None
            record.specialty_id = None
            record.option_id = None
            record.subject_id = None
            record.source_timetable_ids = []
            record.destination_timetable_ids = []

    @api.onchange('school_id')
    def _onchange_school(self):
        for record in self:
            record.level_id = None
            record.source_class_id = None
            record.destination_class_id = None
            record.specialty_id = None
            record.option_id = None
            record.subject_id = None
            record.source_timetable_ids = []
            record.destination_timetable_ids = []

    @api.onchange('level_id')
    def _onchange_level(self):
        for record in self:
            record.source_class_id = None
            record.destination_class_id = None
            record.subject_id = None
            record.source_timetable_ids = []
            record.destination_timetable_ids = []

    @api.onchange('specialty_id')
    def _onchange_specialty(self):
        for record in self:
            record.source_class_id = None
            record.destination_class_id = None
            record.option_id = None
            record.subject_id = None
            record.source_timetable_ids = []
            record.destination_timetable_ids = []

    @api.onchange('option_id')
    def _onchange_option(self):
        for record in self:
            record.source_class_id = None
            record.destination_class_id = None
            record.subject_id = None
            record.source_timetable_ids = []
            record.destination_timetable_ids = []

    @api.onchange('type_cour')
    def _onchange_type_cour(self):
        for record in self:
            record.source_class_id = None
            record.destination_class_id = None
            record.subject_id = None
            record.source_timetable_ids = []
            record.destination_timetable_ids = []

    @api.onchange('source_year_id')
    def _onchange_source_year(self):
        for record in self:
            record.source_class_id = None
            record.subject_id = None
            record.source_timetable_ids = []

    @api.onchange('destination_year_id')
    def _onchange_destination_year(self):
        for record in self:
            record.destination_class_id = None
            record.destination_timetable_ids = []

    def action_copy(self):
        source_class_id = self.env['siantou.ems.core.class'].search([('id', '=', self.source_class_id.id)], limit=1)
        if source_class_id:
            destination_class_id = self.env['siantou.ems.core.class'].search([('id', '=', self.destination_class_id.id)], limit=1)
            if destination_class_id:
                if self.subject_id.id:
                    source_ue_ids = self.subject_id.ue_ids.ids
                    destination_ue_ids = destination_class_id.ue_ids.ids
                    res = list(set(source_ue_ids) & set(destination_ue_ids))
                    if len(source_ue_ids) > 0:
                        if len(res) == 0:
                            raise ValidationError(f"L'unité d\'enseignement du cours doit être copiée dans la classe destination")
                    else:
                        raise ValidationError(f"Les unités d\'enseignement du cours n'existent pas")
                else:
                    source_ue_ids = source_class_id.ue_ids.ids
                    destination_ue_ids = destination_class_id.ue_ids.ids
                    res = list(set(source_ue_ids) & set(destination_ue_ids))
                    if len(source_ue_ids) > 0:
                        if len(source_ue_ids) > len(res):
                            raise ValidationError(f"Les unités d\'enseignement de la classe source doivent être copiées dans la classe destination")
                    else:
                        raise ValidationError(f"Les unités d\'enseignement de la classe source n'existent pas")

                for group_id in source_class_id.group_ids:
                    group = self.env['siantou.ems.core.class.group'].search([
                        ('name', '=', group_id.name),
                        ('class_id', '=', destination_class_id.id),
                    ], limit=1)
                    if not group:
                        destination_class_id.group_ids.create({
                            'name': group_id.name,
                            'class_id': destination_class_id.id,
                        })

                destination_timetable_ids = self.destination_timetable_ids
                # for timetable_id in destination_timetable_ids:
                #     timetable_id.unlink()

                delete_timetable_ids = []

                source_timetable_ids = self.source_timetable_ids
                for timetable_id in source_timetable_ids:
                    if not timetable_id.semester_id.id:
                        delete_timetable_ids.append(timetable_id)
                        continue
                    years = timetable_id.semester_id.year_id.name.split('-')
                    years = [int(y) for y in years]
                    new_years = self.destination_year_id.name.split('-')
                    new_years = [int(y) for y in new_years]

                    semester_id = self.env['siantou.ems.core.year.semester'].search([
                        ('semester_name', '=', timetable_id.semester_id.semester_name),
                        ('year_id', '=', self.destination_year_id.id),
                    ], limit=1)
                    if not semester_id:
                        year, week, day = timetable_id.semester_id.start_time.isocalendar()
                        try:
                            index_year = years.index(year)
                        except ValueError:
                            index_year = -1
                        if index_year != -1 and len(years) > 1 and len(new_years) > 1:
                            year = new_years[index_year]
                        start_time = date.fromisocalendar(year, week, day)

                        year, week, day = timetable_id.semester_id.end_time.isocalendar()
                        try:
                            index_year = years.index(year)
                        except ValueError:
                            index_year = -1
                        if index_year != -1 and len(years) > 1 and len(new_years) > 1:
                            year = new_years[index_year]
                        end_time = date.fromisocalendar(year, week, day)

                        semester_id = self.env['siantou.ems.core.year.semester'].create({
                            'semester_name': timetable_id.semester_id.semester_name,
                            'start_time': start_time,
                            'end_time': end_time,
                            'year_id': self.destination_year_id.id,
                        })
                        level_ids = [(4, level_id.id) for level_id in timetable_id.semester_id.level_ids]
                        # semester_id.level_ids = level_ids
                        semester_id.write({'level_ids': level_ids })

                    group_id = self.env['siantou.ems.timetable.group'].search([
                        ('group_name', '=', timetable_id.group_id.group_name),
                        ('semester_id', '=', semester_id.id),
                        ('is_submit', '=', timetable_id.group_id.is_submit),
                        ('status', '=', timetable_id.group_id.status),
                    ], limit=1)
                    if not group_id:
                        group_id = self.env['siantou.ems.timetable.group'].create({
                            'group_name': timetable_id.group_id.group_name,
                            'semester_id': semester_id.id,
                            'is_submit': timetable_id.group_id.is_submit,
                            'status': timetable_id.group_id.status,
                        })

                    group_ids = []
                    if timetable_id.class_group_id.id:
                        group_ids = destination_class_id.group_ids.filtered(lambda rec: rec.name == timetable_id.class_group_id.name)
                        group_ids = list(group_ids)
                    if len(group_ids) > 0:
                        timetable = self.env['siantou.ems.timetable.timetable'].search([
                            ('class_id', '=', destination_class_id.id),
                            ('class_group_id', '=', group_ids[0].id),
                            ('subject_id', '=', timetable_id.subject_id.id),
                            ('employee_id', '=', timetable_id.employee_id.id),
                            ('date', '=', timetable_id.date),
                            ('start_time', '=', timetable_id.start_time),
                            ('end_time', '=', timetable_id.end_time),
                        ], limit=1)
                        if not timetable:
                            self.env['siantou.ems.timetable.timetable'].create({
                                'department_id': destination_class_id.specialty_id.department_id.id,
                                'school_id': destination_class_id.school_id.id,
                                'level_id': destination_class_id.level_id.id,
                                'specialty_id': destination_class_id.specialty_id.id,
                                'option_id': destination_class_id.option_id.id,
                                'class_id': destination_class_id.id,
                                'class_group_id': group_ids[0].id,
                                'ue_id': timetable_id.ue_id.id,
                                'subject_id': timetable_id.subject_id.id,
                                'building_id': timetable_id.building_id.id,
                                'classroom_id': timetable_id.classroom_id.id,
                                'employee_id': timetable_id.employee_id.id,
                                'date': timetable_id.date,
                                'start_time': timetable_id.start_time,
                                'end_time': timetable_id.end_time,
                                'group_id': group_id.id,
                                'skip_validation': True,
                            })
                    else:
                        timetable = self.env['siantou.ems.timetable.timetable'].search([
                            ('class_id', '=', destination_class_id.id),
                            ('class_group_id', '=', False),
                            ('subject_id', '=', timetable_id.subject_id.id),
                            ('employee_id', '=', timetable_id.employee_id.id),
                            ('date', '=', timetable_id.date),
                            ('start_time', '=', timetable_id.start_time),
                            ('end_time', '=', timetable_id.end_time),
                        ], limit=1)
                        if not timetable:
                            self.env['siantou.ems.timetable.timetable'].create({
                                'department_id': destination_class_id.specialty_id.department_id.id,
                                'school_id': destination_class_id.school_id.id,
                                'level_id': destination_class_id.level_id.id,
                                'specialty_id': destination_class_id.specialty_id.id,
                                'option_id': destination_class_id.option_id.id,
                                'class_id': destination_class_id.id,
                                'ue_id': timetable_id.ue_id.id,
                                'subject_id': timetable_id.subject_id.id,
                                'building_id': timetable_id.building_id.id,
                                'classroom_id': timetable_id.classroom_id.id,
                                'employee_id': timetable_id.employee_id.id,
                                'date': timetable_id.date,
                                'start_time': timetable_id.start_time,
                                'end_time': timetable_id.end_time,
                                'group_id': group_id.id,
                                'skip_validation': True,
                            })

                for timetable_id in delete_timetable_ids:
                    timetable_id.unlink()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
