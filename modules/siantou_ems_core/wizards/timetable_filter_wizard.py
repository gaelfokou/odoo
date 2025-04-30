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

    status = fields.Selection([
        ('0', 'En attente'),
        ('1', 'Présent'),
        ('2', 'Absent'),
        ('3', 'Permissionnaire'),
        ('4', 'Exception'),
    ], 'Statut',
        # default='0',
    )

    specialty_id_domain = fields.Binary(compute='_compute_school_domain', default=[])

    subject_id_domain = fields.Binary(compute='_compute_class_domain', default=[])

    def _default_start_date(self):
        first_time = date.today()
        start_time = first_time + timedelta(days=0)
        if start_time.weekday() != 0:
            start_time = start_time - timedelta(days=start_time.weekday())
        return start_time

    # Date du jour où le cours sera programmé
    start_date = fields.Date(
        'Date de début',
        # default=_default_start_date,
    )

    def _default_end_date(self):
        first_time = date.today()
        start_time = first_time + timedelta(days=0)
        if start_time.weekday() != 0:
            start_time = start_time - timedelta(days=start_time.weekday())
        end_time = start_time + timedelta(days=5)
        return end_time

    # Date du jour où le cours sera programmé
    end_date = fields.Date(
        'Date de fin',
        # default=_default_end_date,
    )

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
            record.ue_id = None
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

    @api.constrains('start_date', 'end_date')
    def _constrains_date(self):
        for record in self:
            if record.start_date and record.end_date:
                if record.start_date > record.end_date:
                    raise ValidationError('La date de fin doit être supérieure ou égale à la date de début')
                # elif record.start_date + relativedelta(months=1) < record.end_date:
                #     raise ValidationError(f"La plage entre la date de début et la date de fin ne doit pas être supérieure 1 mois")

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
        if self.field_of_study_id.id:
            domain.append(('field_of_study_id', '=', self.field_of_study_id.id))
            title.append(self.field_of_study_id.name)
        if self.level_id.id:
            domain.append(('level_id', '=', self.level_id.id))
            title.append(self.level_id.name)
        if self.class_id.id:
            domain.append(('class_id', '=', self.class_id.id))
            title.append(self.class_id.name)
        if self.specialty_id.id:
            domain.append(('specialty_id', '=', self.specialty_id.id))
            title.append(self.specialty_id.name)
        if self.option_id.id:
            domain.append(('option_id', '=', self.option_id.id))
            title.append(self.option_id.name)
        if self.ue_id.id:
            domain.append(('ue_id', '=', self.ue_id.id))
            title.append(self.ue_id.name)
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
        if self.status:
            domain.append(('status', '=', self.status))
        if self.start_date and self.end_date:
            domain.append(('date', '>=', self.start_date))
            domain.append(('date', '<=', self.end_date))

        if len(title) > 0:
            title = '/'.join(title)
        else:
            title = 'Emplois du temps filtrés'

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

    def action_cancel_filter(self):
        action = self.env.ref('siantou_ems_core.action_show_timetable').read()[0]
        action.update({
            'target': 'main',
        })
        return action
