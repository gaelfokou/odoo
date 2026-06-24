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
    'timetable_active': 'Emplois du temps actifs',
    'timetable_not_active': 'Emplois du temps pas actifs',
}

_logger = logging.getLogger(__name__)

class ClassFilterWizard(models.TransientModel):
    _name = 'class.filter.wizard'
    _description = 'Filtre des classes'

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
        'Niveau',
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

    status = fields.Selection([
        ('timetable_available', 'Emplois du temps disponibles'),
        ('timetable_not_available', 'Emplois du temps pas disponibles'),
        ('student_available', 'Étudiants disponibles'),
        ('student_not_available', 'Étudiants pas disponibles'),
        ('student_more_than_or_equal', 'Étudiants plus de ou égal à'),
        ('student_less_than', 'Étudiants moins de'),
        ('timetable_active', 'Emplois du temps actifs'),
        ('timetable_not_active', 'Emplois du temps pas actifs'),
    ], 'Statut',
        # default='timetable_available',
    )

    number_of_student = fields.Integer(
        string='Nombre d\'étudiants',
        default=0,
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
                domain.append(('school_id', '=', record.school_id.id))
            record.specialty_id_domain = domain

    @api.onchange('year_id')
    def _onchange_year(self):
        for record in self:
            record.school_id = None
            record.level_id = None
            record.specialty_id = None
            record.option_id = None

    @api.onchange('school_id')
    def _onchange_school(self):
        for record in self:
            record.level_id = None
            record.specialty_id = None
            record.option_id = None

    @api.onchange('specialty_id')
    def _onchange_specialty(self):
        for record in self:
            record.option_id = None

    def action_filter(self):
        domain = []
        title = []
        if self.year_id.id:
            domain.append(('year_id', '=', self.year_id.id))
            title.append(self.year_id.name)
        if self.school_id.id:
            domain.append(('school_id', '=', self.school_id.id))
            title.append(self.school_id.name)
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
        if self.status:
            if self.status == 'timetable_active':
                domain.append(('is_timetable_active', '=', True))
                title.append(STATUS_CLASS[self.status])
            elif self.status == 'timetable_not_active':
                domain.append(('is_timetable_active', '=', False))
                title.append(STATUS_CLASS[self.status])

        class_ids = []
        classes = self.env['siantou.ems.core.class'].search(domain)
        for classe in classes:
            class_ids.append(classe.id)
        class_ids = list(set(class_ids))

        if self.status:
            if self.status == 'timetable_available':
                domain = [
                    ('class_id', 'in', class_ids),
                ]
                if self.semester_id.id:
                    domain.append(('semester_id', '=', self.semester_id.id))
                    title.append(self.semester_id.name)
                timetable_class_ids = []
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
                for timetable in timetables:
                    timetable_class_ids.append(timetable.class_id.id)
                timetable_class_ids = list(set(timetable_class_ids))
                class_ids = list(filter(lambda i: i in timetable_class_ids, class_ids))
                title.append(STATUS_CLASS[self.status])
            elif self.status == 'timetable_not_available':
                domain = [
                    ('class_id', 'in', class_ids),
                ]
                if self.semester_id.id:
                    domain.append(('semester_id', '=', self.semester_id.id))
                    title.append(self.semester_id.name)
                timetable_class_ids = []
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
                for timetable in timetables:
                    timetable_class_ids.append(timetable.class_id.id)
                timetable_class_ids = list(set(timetable_class_ids))
                class_ids = list(filter(lambda i: i not in timetable_class_ids, class_ids))
                title.append(STATUS_CLASS[self.status])
            elif self.status == 'student_available':
                domain = [
                    ('id', 'in', class_ids),
                ]
                student_class_ids = []
                classes = self.env['siantou.ems.core.class'].search(domain)
                for classe in classes:
                    if len(classe.student_ids.ids) > 0:
                        student_class_ids.append(classe.id)
                student_class_ids = list(set(student_class_ids))
                class_ids = list(filter(lambda i: i in student_class_ids, class_ids))
                title.append(STATUS_CLASS[self.status])
            elif self.status == 'student_not_available':
                domain = [
                    ('id', 'in', class_ids),
                ]
                student_class_ids = []
                classes = self.env['siantou.ems.core.class'].search(domain)
                for classe in classes:
                    if len(classe.student_ids.ids) > 0:
                        student_class_ids.append(classe.id)
                student_class_ids = list(set(student_class_ids))
                class_ids = list(filter(lambda i: i not in student_class_ids, class_ids))
                title.append(STATUS_CLASS[self.status])
            elif self.status == 'student_more_than_or_equal':
                domain = [
                    ('id', 'in', class_ids),
                ]
                student_class_ids = []
                classes = self.env['siantou.ems.core.class'].search(domain)
                for classe in classes:
                    if len(classe.student_ids.ids) >= self.number_of_student:
                        student_class_ids.append(classe.id)
                student_class_ids = list(set(student_class_ids))
                class_ids = list(filter(lambda i: i in student_class_ids, class_ids))
                title.append(STATUS_CLASS[self.status])
                title.append('{} étudiant(s)'.format(self.number_of_student))
            elif self.status == 'student_less_than':
                domain = [
                    ('id', 'in', class_ids),
                ]
                student_class_ids = []
                classes = self.env['siantou.ems.core.class'].search(domain)
                for classe in classes:
                    if len(classe.student_ids.ids) < self.number_of_student:
                        student_class_ids.append(classe.id)
                student_class_ids = list(set(student_class_ids))
                class_ids = list(filter(lambda i: i in student_class_ids, class_ids))
                title.append(STATUS_CLASS[self.status])
                title.append('{} étudiant(s)'.format(self.number_of_student))
        domain = [
            ('id', 'in', class_ids),
        ]

        if len(title) > 0:
            title = ' / '.join(title)
        else:
            title = 'Non spécifié'

        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', title)

        view_id = self.env.ref('siantou_ems_core.class_tree_view').id
        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'siantou.ems.core.class',
            'views': [(view_id, 'tree'), (False, 'form')],
            'view_id': view_id,
            'domain': domain,
            'target': 'main',
        }
