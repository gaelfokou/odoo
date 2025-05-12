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
}

TYPE_COUR = {
    'cj': 'Cours du jour',
    'cs': 'Cours du soir',
}

_logger = logging.getLogger(__name__)

class TimetableFilterWizard(models.TransientModel):
    _name = 'timetable.filter.wizard'
    _description = 'Filtre des emplois du temps'

    # Semestre liée à la programmation de cours
    semester_id = fields.Many2one(
        'siantou.ems.core.year.semester',
        string='Semestre',
        # default=_default_semester,
        related='group_id.semester_id',
        store=True
    )

    year_id = fields.Many2one(
        'siantou.ems.core.year',
        'Année académique',
        related='semester_id.year_id',
        store=True
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
    ], string="Type de cours")

    class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe',
    )

    subject_id = fields.Many2one(
        'siantou.ems.core.subject',
        'Cours',
    )

    # Bâtiment auquel appartient la salle de classe
    building_id = fields.Many2one(
        'siantou.ems.core.building',
        'Bâtiment',
    )

    # Salle liée à la programmation de cours
    classroom_id = fields.Many2one(
        'siantou.ems.core.building.classroom',
        'Salle de classe',
    )

    # Enseignant lié à la programmation de cours
    employee_id = fields.Many2one(
        'hr.employee',
        'Enseignant',
    )

    # Version auquel appartient l'emploi du temps
    group_id = fields.Many2one(
        'siantou.ems.timetable.group',
        'Version',
        required=True,
    )

    date = fields.Date(
        'Date du jour',
    )

    # Heure de début du cours
    start_time = fields.Float(
        'Heure de début',
        default=0,
        widget='time'
    )

    # Heure de fin du cours
    end_time = fields.Float(
        'Heure de fin',
        default=0,
        widget='time'
    )

    status = fields.Selection([
        ('pending', 'En attente'),
        ('progress', 'En cours'),
        ('present', 'Présent'),
        ('absent', 'Absent'),
        ('permission', 'Permission'),
        ('exception', 'Exception'),
    ], 'Statut',
        # default='pending',
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

    # Contrainte logique pour s'assurer que les heures de début et de fin sont définies et que l'heure de fin est supérieure à l'heure de début
    @api.constrains('start_time', 'end_time')
    def _constrains_time(self):
        for record in self:
            if record.end_time < record.start_time:
                raise ValidationError("L'heure de fin du cours doit être supérieure à l'heure de début du cours")

    @api.onchange('group_id')
    def _onchange_group(self):
        for record in self:
            record.semester_id = record.group_id.semester_id.id
            record.school_id = None
            record.field_of_study_id = None
            record.level_id = None
            record.class_id = None
            record.specialty_id = None
            record.option_id = None
            record.subject_id = None

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

    def search_filtered(self, rec):
        result = not (rec.start_time >= self.end_time or rec.end_time <= self.start_time)
        return result

    def action_filter(self):
        domain = []
        title = []
        if self.year_id.id:
            domain.append(('year_id', '=', self.year_id.id))
        if self.semester_id.id:
            domain.append(('semester_id', '=', self.semester_id.id))
        if self.department_id.id:
            domain.append(('department_id', '=', self.department_id.id))
            title.append(self.department_id.name)
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
        if self.building_id.id:
            domain.append(('building_id', '=', self.building_id.id))
            title.append(self.building_id.name)
        if self.classroom_id.id:
            domain.append(('classroom_id', '=', self.classroom_id.id))
            title.append(self.classroom_id.name)
        if self.employee_id.id:
            domain.append(('employee_id', '=', self.employee_id.id))
            title.append(self.employee_id.name)
        if self.group_id.id:
            domain.append(('group_id', '=', self.group_id.id))
        if self.date:
            domain.append(('date', '=', self.date))
            title.append(datetime.strftime(self.date, DATE_FORMAT_FR))
        if self.status:
            domain.append(('status', '=', self.status))
            title.append(STATUS_TIMETABLE[self.status])

        timetable_ids = []
        if self.start_time and self.end_time:
            start_time = TimetableFilterWizard.convert_float_to_time(self.start_time)
            end_time = TimetableFilterWizard.convert_float_to_time(self.end_time)
            title.append('{} - {}'.format(start_time, end_time))
            timetables = self.env['siantou.ems.timetable.timetable'].search(domain).filtered(lambda rec: not (rec.start_time >= self.end_time or rec.end_time <= self.start_time))
            # timetables = self.env['siantou.ems.timetable.timetable'].search(domain).filtered(lambda rec: self.search_filtered(rec))
        else:
            timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
        for timetable in timetables:
            timetable_ids.append(timetable.id)
        timetable_ids = list(set(timetable_ids))

        domain = [('id', 'in', timetable_ids)]

        if len(title) > 0:
            title = '/'.join(title)
        else:
            title = 'Non spécifié'

        self.env['ir.config_parameter'].sudo().set_param(f'filter.{self.env.user.id}', title)

        view_id = self.env.ref('siantou_ems_core.timetable_tree_view').id
        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'siantou.ems.timetable.timetable',
            'views': [(view_id, 'tree')],
            'view_id': view_id,
            'domain' : domain,
            'target': 'main',
        }

    @staticmethod
    def convert_float_to_time(tm, has_second=False):
        tm = str(tm)
        tm = tm.split('.')
        if len(tm[0]) == 1:
            tm[0] = '0{}'.format(tm[0])
        if len(tm[1]) == 1:
            tm[1] = '{}0'.format(tm[1])
        tm = ':'.join(tm)
        if has_second:
            tm = '{}:00'.format(tm)
        return tm
