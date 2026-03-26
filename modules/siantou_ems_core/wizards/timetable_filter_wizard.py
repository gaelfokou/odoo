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

CURRENT_WEEKDAY = {
    '0': 'Lundi',
    '1': 'Mardi',
    '2': 'Mercredi',
    '3': 'Jeudi',
    '4': 'Vendredi',
    '5': 'Samedi',
    '6': 'Dimanche'
}

STATUS_TIMETABLE = {
    'pending': 'En attente',
    'progress': 'En cours',
    'present': 'Présent',
    'absent': 'Absent',
    'permission': 'Permission',
    'exception': 'Exception',
    'exception_start_time_invalid': 'Exception poinçonnement de début absent ou invalide',
    'exception_end_time_invalid': 'Exception poinçonnement de fin absent ou invalide',
    'exception_time_invalid': 'Exception poinçonnement absent ou invalide',
    'exception_reverse': 'Exception poinçonnement de début et de fin inversé',
    'exception_other': 'Exception autre',
    'delay': 'Retard',
    'delay_more_than_or_equal': 'Retard plus de ou égal à',
    'delay_less_than': 'Retard moins de',
    'punctuality': 'Ponctualité',
}

PRINT_TYPE = {
    'school': 'Par école',
    'department': 'Par département',
    'specialty': 'Par spécialité',
    'teacher': 'Par enseignant',
}

TYPE_COUR = {
    'cj': 'Cours du jour',
    'cs': 'Cours du soir',
}

TYPE_PERCENTAGE = {
    'top': 'Top 10',
    'last': 'Last 10',
}

_logger = logging.getLogger(__name__)

class TimetableFilterWizard(models.TransientModel):
    _name = 'timetable.filter.wizard'
    _description = 'Filtre des emplois du temps'

    year_id = fields.Many2one(
        'siantou.ems.core.year',
        'Année académique',
        required=True
    )

    semester_id = fields.Many2one(
        'siantou.ems.core.year.semester',
        string='Semestre',
        related='group_id.semester_id',
        store=True
    )

    group_id = fields.Many2one(
        'siantou.ems.timetable.group',
        string='Version d\'emploi du temps',
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
        store=True
    )

    cycle_id = fields.Many2one(
        'oe.school.course',
        string='Cursus ou Cycle',
        related='field_of_study_id.cycle_id',
        store=True
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Département',
        # related='specialty_id.department_id',
        # store=True
    )

    specialty_id = fields.Many2one(
        'siantou.ems.core.specialty',
        string='Spécialité',
    )

    option_id = fields.Many2one(
        'siantou.ems.core.option',
        string='Option',
    )

    class_group_id = fields.Many2one(
        'siantou.ems.core.class.group',
        string='Groupe de classe',
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
        string='Cours',
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

    def _default_start_date(self):
        start_date = date.today().replace(day=1)
        return start_date

    start_date = fields.Date(
        string='Date de début',
        default=_default_start_date,
    )

    def _default_end_date(self):
        end_date = (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()
        return end_date

    end_date = fields.Date(
        string='Date de fin',
        default=_default_end_date,
    )

    # Heure de début du cours
    start_time = fields.Float(
        'Heure de début',
        default=0.0,
        widget='time'
    )

    # Heure de fin du cours
    end_time = fields.Float(
        'Heure de fin',
        default=0.0,
        widget='time'
    )

    status = fields.Selection([
        ('pending', 'En attente'),
        ('progress', 'En cours'),
        ('present', 'Présent'),
        ('absent', 'Absent'),
        ('permission', 'Permission'),
        ('exception', 'Exception'),
        ('exception_start_time_invalid', 'Exception poinçonnement de début absent ou invalide'),
        ('exception_end_time_invalid', 'Exception poinçonnement de fin absent ou invalide'),
        ('exception_time_invalid', 'Exception poinçonnement absent ou invalide'),
        ('exception_reverse', 'Exception poinçonnement de début et de fin inversé'),
        ('exception_other', 'Exception autre'),
        ('delay', 'Retard'),
        ('delay_more_than_or_equal', 'Retard plus de ou égal à'),
        ('delay_less_than', 'Retard moins de'),
        ('punctuality', 'Ponctualité'),
    ], 'Statut',
        # default='pending',
    )

    number_of_minute = fields.Float(
        string='Nombre de minutes',
        default=0.0,
    )

    has_option = fields.Boolean(
        'Spécialité avec option',
        compute='_compute_has_option', store=True,
    )

    has_group = fields.Boolean(
        'Classe avec groupe',
        compute='_compute_has_group', store=True,
    )

    is_permanent = fields.Boolean(
        'Est un permanent',
        default=False,
    )

    is_temporary = fields.Boolean(
        'Est un vacataire',
        default=False,
    )

    print_type = fields.Selection([
        ('school', 'Par école'),
        ('department', 'Par département'),
        ('specialty', 'Par spécialité'),
        ('teacher', 'Par enseignant'),
    ], 'Type d\'impression',
        # default='school',
    )

    @api.depends('specialty_id')
    def _compute_has_option(self):
        for record in self:
            option_ids = self.env['siantou.ems.core.option'].search([
                ('specialty_id', '=', record.specialty_id.id),
            ])

            record.has_option = len(option_ids.ids) > 0

    @api.onchange('specialty_id')
    def _onchange_has_option(self):
        for record in self:
            option_ids = self.env['siantou.ems.core.option'].search([
                ('specialty_id', '=', record.specialty_id.id),
            ])

            record.has_option = len(option_ids.ids) > 0

    @api.depends('class_id')
    def _compute_has_group(self):
        for record in self:
            group_ids = self.env['siantou.ems.core.class.group'].search([
                ('class_id', '=', record.class_id.id),
            ])

            record.has_group = len(group_ids.ids) > 0

    @api.onchange('class_id')
    def _onchange_has_group(self):
        for record in self:
            group_ids = self.env['siantou.ems.core.class.group'].search([
                ('class_id', '=', record.class_id.id),
            ])

            record.has_group = len(group_ids.ids) > 0

    department_id_domain = fields.Binary(compute='_compute_department_domain', default=[])

    specialty_id_domain = fields.Binary(compute='_compute_school_domain', default=[])

    subject_id_domain = fields.Binary(compute='_compute_class_domain', default=[])

    class_id_domain = fields.Binary(compute='_compute_all_domain', default=[])

    school_id_domain = fields.Binary(compute='_compute_group_domain', default=[])

    employee_id_domain = fields.Binary(compute='_compute_employee_domain', default=[])

    @api.depends('year_id', 'school_id', 'level_id', 'field_of_study_id', 'specialty_id', 'option_id', 'type_cour')
    def _compute_all_domain(self):
        for record in self:
            domain = []
            if record.year_id.id:
                domain.append(('year_id', '=', record.year_id.id))
            if record.school_id.id:
                domain.append(('school_id', '=', record.school_id.id))
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

    @api.constrains('start_date', 'end_date')
    def _constrains_date(self):
        for record in self:
            if record.start_date > record.end_date:
                raise ValidationError("La date de fin doit être supérieure à la date de début")

    @api.constrains('start_time', 'end_time')
    def _constrains_time(self):
        for record in self:
            if record.start_time < 0.0 or record.end_time < 0.0 or record.start_time > 23.59 or record.end_time > 23.59:
                raise ValidationError("Vous devez définir des heures de début et de fin corrects")
            elif record.start_time > record.end_time:
                raise ValidationError("L'heure de fin du cours doit être supérieure à l'heure de début du cours")

    @api.onchange('year_id')
    def _onchange_year(self):
        for record in self:
            record.group_id = None
            record.school_id = None
            record.field_of_study_id = None
            record.level_id = None
            record.class_id = None
            record.specialty_id = None
            record.option_id = None
            record.subject_id = None

    @api.onchange('semester_id')
    def _onchange_semester(self):
        for record in self:
            record.group_id = None
            record.school_id = None
            record.field_of_study_id = None
            record.level_id = None
            record.class_id = None
            record.specialty_id = None
            record.option_id = None
            record.subject_id = None

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
    def _compute_department_domain(self):
        for record in self:
            department_ids = record.group_id.department_ids
            domain = []
            if record.school_id.id:
                domain.append(('school_id', '=', record.school_id.id))
            if len(department_ids.ids) > 0:
                domain.append(('id', 'in', department_ids.ids))
            record.department_id_domain = domain

    @api.depends('group_id', 'school_id', 'department_id')
    def _compute_school_domain(self):
        for record in self:
            department_ids = record.group_id.department_ids
            domain = []
            if record.school_id.id:
                domain.append(('school_id', '=', record.school_id.id))
            if record.department_id.id:
                domain.append(('department_id', '=', record.department_id.id))
            if len(department_ids.ids) > 0:
                domain.append(('department_id', 'in', department_ids.ids))
            record.specialty_id_domain = domain

    @api.depends('is_permanent', 'is_temporary')
    def _compute_employee_domain(self):
        for record in self:
            domain = [
                ('is_teacher', '=', True)
            ]
            if not record.is_permanent or not record.is_temporary:
                if record.is_permanent:
                    domain.append(('is_permanent', '=', True))
                if record.is_temporary:
                    domain.append(('is_permanent', '=', False))
            record.employee_id_domain = domain

    @api.onchange('group_id')
    def _onchange_group(self):
        for record in self:
            record.school_id = None
            record.field_of_study_id = None
            record.level_id = None
            record.class_id = None
            record.specialty_id = None
            record.option_id = None
            record.subject_id = None
            record.employee_id = None

    @api.onchange('is_permanent', 'is_temporary')
    def _onchange_employee(self):
        for record in self:
            record.employee_id = None

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
            if not record.department_id.id:
                record.department_id = record.specialty_id.department_id

    # @api.onchange('department_id')
    # def _onchange_department(self):
    #     for record in self:
    #         record.specialty_id = None
    #         record.class_id = None
    #         record.option_id = None
    #         record.subject_id = None

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
                domain = [
                    ('ue_ids', 'in', ue_ids.ids)
                ]
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
            title.append(self.year_id.name)
        if self.semester_id.id:
            domain.append(('semester_id', '=', self.semester_id.id))
            title.append(self.semester_id.name)
        if self.school_id.id:
            domain.append(('school_id', '=', self.school_id.id))
            title.append(self.school_id.name)
        if self.department_id.id:
            domain.append(('department_id', '=', self.department_id.id))
            title.append(self.department_id.name)
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
        if self.class_group_id.id:
            domain.append(('class_group_id', '=', self.class_group_id.id))
            title.append(self.class_group_id.name)
        if self.subject_id.id:
            domain.append(('subject_id', '=', self.subject_id.id))
            title.append(self.subject_id.name)
        if self.building_id.id:
            domain.append(('building_id', '=', self.building_id.id))
            title.append(self.building_id.name)
        if self.classroom_id.id:
            domain.append(('classroom_id', '=', self.classroom_id.id))
            title.append(self.classroom_id.name)
        domain.append(('employee_id.is_teacher', '=', True))
        if not self.is_permanent or not self.is_temporary:
            if self.is_permanent:
                domain.append(('employee_id.is_permanent', '=', True))
                title.append('Est un permanent')
            if self.is_temporary:
                domain.append(('employee_id.is_permanent', '=', False))
                title.append('Est un vacataire')
        if self.employee_id.id:
            domain.append(('employee_id', '=', self.employee_id.id))
            title.append(self.employee_id.name)
        if self.group_id.id:
            domain.append(('group_id', '=', self.group_id.id))
            title.append(self.group_id.name)
        else:
            group_ids = self.env['siantou.ems.timetable.group'].search(['|', '|', ('create_uid', '=', self.env.user.id), ('read_user_ids', '=', self.env.user.id), ('write_user_ids', '=', self.env.user.id)])
            domain.append(('group_id', 'in', group_ids.ids))

        order = 'date asc, id asc'

        if self.status:
            if self.status == 'delay':
                domain.append(('status', '=', 'present'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                timetables = timetables.filtered(lambda rec: rec.date and rec.day_of_week and TimetableFilterWizard.compare_float_time(rec.date, rec.worked_start_time, rec.start_time) > 0.0)
            elif self.status == 'delay_more_than_or_equal':
                domain.append(('status', '=', 'present'))
                title.append(STATUS_TIMETABLE[self.status])
                title.append('{} minute(s)'.format(self.number_of_minute))
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                timetables = timetables.filtered(lambda rec: rec.date and rec.day_of_week and TimetableFilterWizard.compare_float_time(rec.date, rec.worked_start_time, rec.start_time) >= self.number_of_minute)
            elif self.status == 'delay_less_than':
                domain.append(('status', '=', 'present'))
                title.append(STATUS_TIMETABLE[self.status])
                title.append('{} minute(s)'.format(self.number_of_minute))
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                timetables = timetables.filtered(lambda rec: rec.date and rec.day_of_week and TimetableFilterWizard.compare_float_time(rec.date, rec.worked_start_time, rec.start_time) > 0.0 and TimetableFilterWizard.compare_float_time(rec.date, rec.worked_start_time, rec.start_time) < self.number_of_minute)
            elif self.status == 'punctuality':
                domain.append(('status', '=', 'present'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                timetables = timetables.filtered(lambda rec: rec.date and rec.day_of_week and TimetableFilterWizard.compare_float_time(rec.date, rec.worked_start_time, rec.start_time) == 0.0)
            elif self.status == 'exception_start_time_invalid':
                domain.append(('status', '=', 'exception'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                timetables = timetables.filtered(lambda rec: rec.reason and rec.reason == 'Poinçonnement de début absent ou invalide')
            elif self.status == 'exception_end_time_invalid':
                domain.append(('status', '=', 'exception'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                timetables = timetables.filtered(lambda rec: rec.reason and rec.reason == 'Poinçonnement de fin absent ou invalide')
            elif self.status == 'exception_time_invalid':
                domain.append(('status', '=', 'exception'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                timetables = timetables.filtered(lambda rec: rec.reason and rec.reason == 'Poinçonnement absent ou invalide')
            elif self.status == 'exception_reverse':
                domain.append(('status', '=', 'exception'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                timetables = timetables.filtered(lambda rec: rec.reason and rec.reason == 'Poinçonnement de début et de fin inversé')
            elif self.status == 'exception_other':
                domain.append(('status', '=', 'exception'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                timetables = timetables.filtered(lambda rec: rec.reason and rec.reason not in ['Poinçonnement de début absent ou invalide', 'Poinçonnement de fin absent ou invalide', 'Poinçonnement absent ou invalide', 'Poinçonnement de début et de fin inversé'])
            else:
                domain.append(('status', '=', self.status))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
        else:
            timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
        if self.start_date and self.end_date:
            start_date = datetime.strftime(self.start_date, DATE_FORMAT_FR)
            end_date = datetime.strftime(self.end_date, DATE_FORMAT_FR)
            title.append('{} - {}'.format(start_date, end_date))
            timetables = timetables.filtered(lambda rec: rec.date and rec.day_of_week and rec.date >= self.start_date and rec.date <= self.end_date)
        if self.start_time and self.end_time:
            start_time = TimetableFilterWizard.convert_float_to_time(self.start_time)
            end_time = TimetableFilterWizard.convert_float_to_time(self.end_time)
            title.append('{} - {}'.format(start_time, end_time))
            timetables = timetables.filtered(lambda rec: not (rec.start_time >= self.end_time or rec.end_time <= self.start_time))
            # timetables = timetables.filtered(lambda rec: self.search_filtered(rec))

        timetable_ids = []
        key_timetables = {}
        for timetable in timetables:
            if not timetable.date or not timetable.day_of_week or not timetable.employee_id.id:
                continue

            end_time = TimetableFilterWizard.convert_float_to_time(timetable.end_time, has_second=True)
            start_time = TimetableFilterWizard.convert_float_to_time(timetable.start_time, has_second=True)
            key = '{}-{}-{}-{}'.format(timetable.class_id.id, timetable.date, start_time, end_time)
            if key not in key_timetables:
                key_timetables[key] = timetable
            else:
                continue

            timetable_ids.append(timetable.id)
        timetable_ids = list(set(timetable_ids))

        domain = [
            ('id', 'in', timetable_ids)
        ]

        if len(title) > 0:
            title = ' / '.join(title)
        else:
            title = 'Non spécifié'

        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', title)

        tree_view = self.env.ref('siantou_ems_core.timetable_tree_view').id
        calendar_view = self.env.ref('siantou_ems_core.timetable_calendar_view').id
        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form,calendar',
            'res_model': 'siantou.ems.timetable.timetable',
            'views': [(tree_view, 'tree'), (False, 'form'), (calendar_view, 'calendar')],
            'view_id': tree_view,
            'domain': domain,
            'target': 'main',
        }

    def action_print_cumulative_percentage_pdf(self, sort_type=None, print_percentage=True):
        current_date = self.start_date
        current_start_date = current_date - timedelta(days=current_date.weekday())
        current_end_date = current_start_date + timedelta(days=6)
        start_date = datetime.strftime(current_start_date, DATE_FORMAT_FR)
        end_date = datetime.strftime(current_end_date, DATE_FORMAT_FR)
        data = {}
        try:
            self.start_date = current_start_date
            self.end_date = current_end_date
            key = '{}-{}'.format(current_start_date, current_end_date)
            data[key] = self.action_print_percentage_pdf(print_percentage=False)
        except UserError as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

        filter_title = self.env['ir.config_parameter'].sudo().get_param(f'siantou.filter_user_{self.env.user.id}', '')

        try:
            current_start_date = current_date.replace(day=1)
            current_end_date = (datetime(current_date.year, current_date.month, current_date.day) + relativedelta(months=+1, day=1, days=-1)).date()
            self.start_date = current_start_date
            self.end_date = current_end_date
            key = '{}-{}'.format(current_start_date, current_end_date)
            data[key] = self.action_print_percentage_pdf(print_percentage=False)
        except UserError as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

        try:
            current_start_date = current_date.replace(month=1, day=1)
            current_end_date = current_date.replace(month=12, day=31)
            self.start_date = current_start_date
            self.end_date = current_end_date
            key = '{}-{}'.format(current_start_date, current_end_date)
            data[key] = self.action_print_percentage_pdf(print_percentage=False)
        except UserError as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

        all_data = {
            'docdata': {}
        }
        for i, key in enumerate(list(data.keys())[::-1]):
            all_data['docdata']['label'] = data[key]['docdata']['label']
            all_data['docdata']['title'] = 'Cumulation {}'.format(data[key]['docdata']['title'])
            all_data['docdata']['filter'] = filter_title
            all_data['docdata']['sort_type'] = data[key]['docdata']['sort_type']
            all_data['docdata']['status'] = data[key]['docdata']['status']
            all_data['docdata']['cumulative'] = True
            if 'timetable_percentage_data' not in all_data['docdata']:
                all_data['docdata']['timetable_percentage_data'] = data[key]['docdata']['timetable_percentage_data']
                for k in all_data['docdata']['timetable_percentage_data'].keys():
                    all_data['docdata']['timetable_percentage_data'][k]['month_percentage'] = 0.0
                    all_data['docdata']['timetable_percentage_data'][k]['month_class'] = ''
                    all_data['docdata']['timetable_percentage_data'][k]['week_percentage'] = 0.0
                    all_data['docdata']['timetable_percentage_data'][k]['week_class'] = ''
            else:
                for k in all_data['docdata']['timetable_percentage_data'].keys():
                    if i == 1:
                        if k in data[key]['docdata']['timetable_percentage_data']:
                            all_data['docdata']['timetable_percentage_data'][k]['month_percentage'] = data[key]['docdata']['timetable_percentage_data'][k]['percentage']
                            all_data['docdata']['timetable_percentage_data'][k]['month_class'] = data[key]['docdata']['timetable_percentage_data'][k]['class']
                        else:
                            all_data['docdata']['timetable_percentage_data'][k]['month_percentage'] = 0.0
                            all_data['docdata']['timetable_percentage_data'][k]['month_class'] = ''
                    else:
                        if k in data[key]['docdata']['timetable_percentage_data']:
                            all_data['docdata']['timetable_percentage_data'][k]['week_percentage'] = data[key]['docdata']['timetable_percentage_data'][k]['percentage']
                            all_data['docdata']['timetable_percentage_data'][k]['week_class'] = data[key]['docdata']['timetable_percentage_data'][k]['class']
                        else:
                            all_data['docdata']['timetable_percentage_data'][k]['week_percentage'] = 0.0
                            all_data['docdata']['timetable_percentage_data'][k]['week_class'] = ''

        self.end_date = datetime.strptime(end_date, DATE_FORMAT_FR).date()
        self.start_date = datetime.strptime(start_date, DATE_FORMAT_FR).date()

        if len(all_data['docdata'].keys()) == 0:
            raise UserError('Aucune donnée trouvée')
        report_action = self.env.ref('siantou_ems_core.action_report_timetable_percentage')
        report_action.update({
            'name': '{} du {} - {} PDF'.format(all_data['docdata']['title'], start_date, end_date),
        })
        return report_action.report_action(self, data=all_data)

    def action_print_percentage_pdf(self, sort_type=None, print_percentage=True):
        domain = []
        title = []
        if self.year_id.id:
            domain.append(('year_id', '=', self.year_id.id))
            title.append(self.year_id.name)
        if self.semester_id.id:
            domain.append(('semester_id', '=', self.semester_id.id))
            title.append(self.semester_id.name)
        if self.school_id.id:
            domain.append(('school_id', '=', self.school_id.id))
            title.append(self.school_id.name)
        if self.department_id.id:
            domain.append(('department_id', '=', self.department_id.id))
            title.append(self.department_id.name)
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
        if self.class_group_id.id:
            domain.append(('class_group_id', '=', self.class_group_id.id))
            title.append(self.class_group_id.name)
        if self.subject_id.id:
            domain.append(('subject_id', '=', self.subject_id.id))
            title.append(self.subject_id.name)
        if self.building_id.id:
            domain.append(('building_id', '=', self.building_id.id))
            title.append(self.building_id.name)
        if self.classroom_id.id:
            domain.append(('classroom_id', '=', self.classroom_id.id))
            title.append(self.classroom_id.name)
        domain.append(('employee_id.is_teacher', '=', True))
        if not self.is_permanent or not self.is_temporary:
            if self.is_permanent:
                domain.append(('employee_id.is_permanent', '=', True))
                title.append('Est un permanent')
            if self.is_temporary:
                domain.append(('employee_id.is_permanent', '=', False))
                title.append('Est un vacataire')
        if self.employee_id.id:
            domain.append(('employee_id', '=', self.employee_id.id))
            title.append(self.employee_id.name)
        if self.group_id.id:
            domain.append(('group_id', '=', self.group_id.id))
            title.append(self.group_id.name)
        else:
            group_ids = self.env['siantou.ems.timetable.group'].search(['|', '|', ('create_uid', '=', self.env.user.id), ('read_user_ids', '=', self.env.user.id), ('write_user_ids', '=', self.env.user.id)])
            domain.append(('group_id', 'in', group_ids.ids))

        order = 'date asc, id asc'

        all_domain = []
        all_domain += domain
        all_domain.append(('status', '!=', 'pending'))
        all_timetables = self.env['siantou.ems.timetable.timetable'].search(all_domain, order=order).sorted(lambda rec: (rec.date, rec.id))

        if self.status:
            if self.status == 'delay':
                domain.append(('status', '=', 'present'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                timetables = timetables.filtered(lambda rec: rec.date and rec.day_of_week and TimetableFilterWizard.compare_float_time(rec.date, rec.worked_start_time, rec.start_time) >= 0.0)
            elif self.status == 'delay_more_than_or_equal':
                domain.append(('status', '=', 'present'))
                title.append(STATUS_TIMETABLE[self.status])
                title.append('{} minute(s)'.format(self.number_of_minute))
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                timetables = timetables.filtered(lambda rec: rec.date and rec.day_of_week and TimetableFilterWizard.compare_float_time(rec.date, rec.worked_start_time, rec.start_time) >= self.number_of_minute)
            elif self.status == 'delay_less_than':
                domain.append(('status', '=', 'present'))
                title.append(STATUS_TIMETABLE[self.status])
                title.append('{} minute(s)'.format(self.number_of_minute))
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                timetables = timetables.filtered(lambda rec: rec.date and rec.day_of_week and TimetableFilterWizard.compare_float_time(rec.date, rec.worked_start_time, rec.start_time) > 0.0 and TimetableFilterWizard.compare_float_time(rec.date, rec.worked_start_time, rec.start_time) < self.number_of_minute)
            elif self.status == 'absent':
                domain.append(('status', 'in', ['present', 'absent']))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
            elif self.status == 'punctuality':
                domain.append(('status', 'in', ['present', 'absent']))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                timetables = timetables.filtered(lambda rec: rec.date and rec.day_of_week and (rec.status == 'absent' or (rec.status == 'present' and TimetableFilterWizard.compare_float_time(rec.date, rec.worked_start_time, rec.start_time) == 0.0)))
            elif self.status == 'exception_start_time_invalid':
                domain.append(('status', '=', 'exception'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                timetables = timetables.filtered(lambda rec: rec.reason and rec.reason == 'Poinçonnement de début absent ou invalide')
            elif self.status == 'exception_end_time_invalid':
                domain.append(('status', '=', 'exception'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                timetables = timetables.filtered(lambda rec: rec.reason and rec.reason == 'Poinçonnement de fin absent ou invalide')
            elif self.status == 'exception_time_invalid':
                domain.append(('status', '=', 'exception'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                timetables = timetables.filtered(lambda rec: rec.reason and rec.reason == 'Poinçonnement absent ou invalide')
            elif self.status == 'exception_reverse':
                domain.append(('status', '=', 'exception'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                timetables = timetables.filtered(lambda rec: rec.reason and rec.reason == 'Poinçonnement de début et de fin inversé')
            elif self.status == 'exception_other':
                domain.append(('status', '=', 'exception'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
                timetables = timetables.filtered(lambda rec: rec.reason and rec.reason not in ['Poinçonnement de début absent ou invalide', 'Poinçonnement de fin absent ou invalide', 'Poinçonnement absent ou invalide', 'Poinçonnement de début et de fin inversé'])
            else:
                domain.append(('status', '=', self.status))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
        else:
            timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))

        if sort_type:
            title.append(TYPE_PERCENTAGE[sort_type])

        if self.start_date and self.end_date:
            start_date = datetime.strftime(self.start_date, DATE_FORMAT_FR)
            end_date = datetime.strftime(self.end_date, DATE_FORMAT_FR)
            title.append('{} - {}'.format(start_date, end_date))
            timetables = timetables.filtered(lambda rec: rec.date and rec.day_of_week and rec.date >= self.start_date and rec.date <= self.end_date)
            all_timetables = all_timetables.filtered(lambda rec: rec.date and rec.day_of_week and rec.date >= self.start_date and rec.date <= self.end_date)
        if self.start_time and self.end_time:
            start_time = TimetableFilterWizard.convert_float_to_time(self.start_time)
            end_time = TimetableFilterWizard.convert_float_to_time(self.end_time)
            title.append('{} - {}'.format(start_time, end_time))
            timetables = timetables.filtered(lambda rec: not (rec.start_time >= self.end_time or rec.end_time <= self.start_time))
            all_timetables = all_timetables.filtered(lambda rec: not (rec.start_time >= self.end_time or rec.end_time <= self.start_time))
            # timetables = timetables.filtered(lambda rec: self.search_filtered(rec))

        timetables = list(timetables)

        timetable_ids = []
        key_timetables = {}
        for timetable in timetables:
            if not timetable.date or not timetable.day_of_week or not timetable.employee_id.id:
                continue

            end_time = TimetableFilterWizard.convert_float_to_time(timetable.end_time, has_second=True)
            start_time = TimetableFilterWizard.convert_float_to_time(timetable.start_time, has_second=True)
            key = '{}-{}-{}-{}'.format(timetable.class_id.id, timetable.date, start_time, end_time)
            if key not in key_timetables:
                key_timetables[key] = timetable
            else:
                continue

            timetable_ids.append(timetable.id)
        timetable_ids = list(set(timetable_ids))

        domain = [
            ('id', 'in', timetable_ids)
        ]

        all_timetable_ids = []
        key_all_timetables = {}
        for timetable in all_timetables:
            if not timetable.date or not timetable.day_of_week or not timetable.employee_id.id:
                continue

            end_time = TimetableFilterWizard.convert_float_to_time(timetable.end_time, has_second=True)
            start_time = TimetableFilterWizard.convert_float_to_time(timetable.start_time, has_second=True)
            key = '{}-{}-{}-{}'.format(timetable.class_id.id, timetable.date, start_time, end_time)
            if key not in key_all_timetables:
                key_all_timetables[key] = timetable
            else:
                continue

            all_timetable_ids.append(timetable.id)
        all_timetable_ids = list(set(all_timetable_ids))

        all_domain = [
            ('id', 'in', all_timetable_ids)
        ]

        if len(title) > 0:
            title = ' / '.join(title)
        else:
            title = 'Non spécifié'

        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', title)

        if len(timetable_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')
        report_data = self.env['timetable.print.wizard'].create({})
        data = report_data.print_timetable_percentage_report_data(domains=domain, all_domains=all_domain, school=self.school_id, status=self.status, sort_type=sort_type, print_type=self.print_type)

        if self.school_id.id:
            data['docdata']['title'] = '{} {}'.format(data['docdata']['title'], self.school_id.name)

        if len(data['docdata']['timetable_percentage_data'].keys()) == 0:
            raise UserError('Aucune donnée trouvée')
        if print_percentage:
            start_date = datetime.strftime(self.start_date, DATE_FORMAT_FR)
            end_date = datetime.strftime(self.end_date, DATE_FORMAT_FR)

            report_action = self.env.ref('siantou_ems_core.action_report_timetable_percentage')
            report_action.update({
                'name': '{} du {} - {} PDF'.format(data['docdata']['title'], start_date, end_date),
            })
            return report_action.report_action(self, data=data)
        else:
            return data

    def action_print_top_percentage_pdf(self):
        data = self.action_print_percentage_pdf(sort_type='top', print_percentage=False)

        start_date = datetime.strftime(self.start_date, DATE_FORMAT_FR)
        end_date = datetime.strftime(self.end_date, DATE_FORMAT_FR)

        report_action = self.env.ref('siantou_ems_core.action_report_timetable_percentage')
        report_action.update({
            'name': '{} du {} - {} PDF'.format(data['docdata']['title'], start_date, end_date),
        })
        return report_action.report_action(self, data=data)

    def action_print_last_percentage_pdf(self):
        data = self.action_print_percentage_pdf(sort_type='last', print_percentage=False)

        start_date = datetime.strftime(self.start_date, DATE_FORMAT_FR)
        end_date = datetime.strftime(self.end_date, DATE_FORMAT_FR)

        report_action = self.env.ref('siantou_ems_core.action_report_timetable_percentage')
        report_action.update({
            'name': '{} du {} - {} PDF'.format(data['docdata']['title'], start_date, end_date),
        })
        return report_action.report_action(self, data=data)

    def sort_timetable_percentage(self, timetable_percentage):
        percentage = timetable_percentage[1]['percentage']
        return percentage

    def sort_timetable_hours(self, timetable_percentage):
        worked_time = timetable_percentage[1]['worked_time']
        return worked_time

    def action_print_compare_percentage_pdf(self):
        start_date = datetime.strftime(self.start_date, DATE_FORMAT_FR)
        end_date = datetime.strftime(self.end_date, DATE_FORMAT_FR)
        data = {}
        try:
            key = '{}-{}'.format(self.start_date, self.end_date)
            data[key] = self.action_print_percentage_pdf(print_percentage=False)
        except UserError as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

        filter_title = self.env['ir.config_parameter'].sudo().get_param(f'siantou.filter_user_{self.env.user.id}', '')

        try:
            diff = self.end_date - self.start_date
            self.start_date = self.start_date - timedelta(days=diff.days+1)
            self.end_date = self.end_date - timedelta(days=diff.days+1)
            key = '{}-{}'.format(self.start_date, self.end_date)
            data[key] = self.action_print_percentage_pdf(print_percentage=False)
        except UserError as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

        all_data = {
            'docdata': {}
        }
        for key in data.keys():
            all_data['docdata']['label'] = data[key]['docdata']['label']
            all_data['docdata']['title'] = 'Comparaison {}'.format(data[key]['docdata']['title'])
            all_data['docdata']['filter'] = filter_title
            all_data['docdata']['sort_type'] = data[key]['docdata']['sort_type']
            all_data['docdata']['status'] = data[key]['docdata']['status']
            all_data['docdata']['compare'] = True
            if 'timetable_percentage_data' not in all_data['docdata']:
                all_data['docdata']['timetable_percentage_data'] = data[key]['docdata']['timetable_percentage_data']
            else:
                for k in all_data['docdata']['timetable_percentage_data'].keys():
                    if k in data[key]['docdata']['timetable_percentage_data']:
                        all_data['docdata']['timetable_percentage_data'][k]['previous_percentage'] = data[key]['docdata']['timetable_percentage_data'][k]['percentage']
                        all_data['docdata']['timetable_percentage_data'][k]['previous_class'] = data[key]['docdata']['timetable_percentage_data'][k]['class']
                        if self.status and self.status in ['present', 'punctuality']:
                            if all_data['docdata']['timetable_percentage_data'][k]['percentage'] > data[key]['docdata']['timetable_percentage_data'][k]['percentage']:
                                progress = all_data['docdata']['timetable_percentage_data'][k]['percentage'] - data[key]['docdata']['timetable_percentage_data'][k]['percentage']
                                progress = round(progress, 2)
                                all_data['docdata']['timetable_percentage_data'][k]['progress'] = '+{}'.format(progress)
                                all_data['docdata']['timetable_percentage_data'][k]['progress_class'] = 'text-success'
                            elif all_data['docdata']['timetable_percentage_data'][k]['percentage'] < data[key]['docdata']['timetable_percentage_data'][k]['percentage']:
                                progress = data[key]['docdata']['timetable_percentage_data'][k]['percentage'] - all_data['docdata']['timetable_percentage_data'][k]['percentage']
                                progress = round(progress, 2)
                                all_data['docdata']['timetable_percentage_data'][k]['progress'] = '-{}'.format(progress)
                                all_data['docdata']['timetable_percentage_data'][k]['progress_class'] = 'text-danger'
                            else:
                                all_data['docdata']['timetable_percentage_data'][k]['progress'] = '='
                                all_data['docdata']['timetable_percentage_data'][k]['progress_class'] = 'text-warning'
                        else:
                            if all_data['docdata']['timetable_percentage_data'][k]['percentage'] > data[key]['docdata']['timetable_percentage_data'][k]['percentage']:
                                progress = all_data['docdata']['timetable_percentage_data'][k]['percentage'] - data[key]['docdata']['timetable_percentage_data'][k]['percentage']
                                progress = round(progress, 2)
                                all_data['docdata']['timetable_percentage_data'][k]['progress'] = '+{}'.format(progress)
                                all_data['docdata']['timetable_percentage_data'][k]['progress_class'] = 'text-danger'
                            elif all_data['docdata']['timetable_percentage_data'][k]['percentage'] < data[key]['docdata']['timetable_percentage_data'][k]['percentage']:
                                progress = data[key]['docdata']['timetable_percentage_data'][k]['percentage'] - all_data['docdata']['timetable_percentage_data'][k]['percentage']
                                progress = round(progress, 2)
                                all_data['docdata']['timetable_percentage_data'][k]['progress'] = '-{}'.format(progress)
                                all_data['docdata']['timetable_percentage_data'][k]['progress_class'] = 'text-success'
                            else:
                                all_data['docdata']['timetable_percentage_data'][k]['progress'] = '='
                                all_data['docdata']['timetable_percentage_data'][k]['progress_class'] = 'text-warning'
                    else:
                        all_data['docdata']['timetable_percentage_data'][k]['previous_percentage'] = ''
                        all_data['docdata']['timetable_percentage_data'][k]['previous_class'] = ''
                        all_data['docdata']['timetable_percentage_data'][k]['progress'] = ''
                        all_data['docdata']['timetable_percentage_data'][k]['progress_class'] = ''

        self.end_date = datetime.strptime(end_date, DATE_FORMAT_FR).date()
        self.start_date = datetime.strptime(start_date, DATE_FORMAT_FR).date()

        if len(all_data['docdata'].keys()) == 0:
            raise UserError('Aucune donnée trouvée')
        report_action = self.env.ref('siantou_ems_core.action_report_timetable_percentage')
        report_action.update({
            'name': '{} du {} - {} PDF'.format(all_data['docdata']['title'], start_date, end_date),
        })
        return report_action.report_action(self, data=all_data)

    def action_print_hours_percentage_pdf(self):
        domain = []
        title = []
        if self.year_id.id:
            domain.append(('year_id', '=', self.year_id.id))
            title.append(self.year_id.name)
        if self.semester_id.id:
            domain.append(('semester_id', '=', self.semester_id.id))
            title.append(self.semester_id.name)
        if self.school_id.id:
            domain.append(('school_id', '=', self.school_id.id))
            title.append(self.school_id.name)
        if self.department_id.id:
            domain.append(('department_id', '=', self.department_id.id))
            title.append(self.department_id.name)
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
        if self.class_group_id.id:
            domain.append(('class_group_id', '=', self.class_group_id.id))
            title.append(self.class_group_id.name)
        if self.subject_id.id:
            domain.append(('subject_id', '=', self.subject_id.id))
            title.append(self.subject_id.name)
        if self.building_id.id:
            domain.append(('building_id', '=', self.building_id.id))
            title.append(self.building_id.name)
        if self.classroom_id.id:
            domain.append(('classroom_id', '=', self.classroom_id.id))
            title.append(self.classroom_id.name)
        domain.append(('employee_id.is_teacher', '=', True))
        if self.group_id.id:
            domain.append(('group_id', '=', self.group_id.id))
            title.append(self.group_id.name)
        else:
            group_ids = self.env['siantou.ems.timetable.group'].search(['|', '|', ('create_uid', '=', self.env.user.id), ('read_user_ids', '=', self.env.user.id), ('write_user_ids', '=', self.env.user.id)])
            domain.append(('group_id', 'in', group_ids.ids))

        order = 'date asc, id asc'

        all_domain = []
        all_domain += domain
        all_timetables = self.env['siantou.ems.timetable.timetable'].search(all_domain, order=order).sorted(lambda rec: (rec.date, rec.id))

        if not self.is_permanent or not self.is_temporary:
            if self.is_permanent:
                domain.append(('employee_id.is_permanent', '=', True))
                title.append('Est un permanent')
            if self.is_temporary:
                domain.append(('employee_id.is_permanent', '=', False))
                title.append('Est un vacataire')
        if self.employee_id.id:
            domain.append(('employee_id', '=', self.employee_id.id))
            title.append(self.employee_id.name)

        timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))

        if self.start_date and self.end_date:
            start_date = datetime.strftime(self.start_date, DATE_FORMAT_FR)
            end_date = datetime.strftime(self.end_date, DATE_FORMAT_FR)
            title.append('{} - {}'.format(start_date, end_date))
            timetables = timetables.filtered(lambda rec: rec.date and rec.day_of_week and rec.date >= self.start_date and rec.date <= self.end_date)
            all_timetables = all_timetables.filtered(lambda rec: rec.date and rec.day_of_week and rec.date >= self.start_date and rec.date <= self.end_date)
        if self.start_time and self.end_time:
            start_time = TimetableFilterWizard.convert_float_to_time(self.start_time)
            end_time = TimetableFilterWizard.convert_float_to_time(self.end_time)
            title.append('{} - {}'.format(start_time, end_time))
            timetables = timetables.filtered(lambda rec: not (rec.start_time >= self.end_time or rec.end_time <= self.start_time))
            all_timetables = all_timetables.filtered(lambda rec: not (rec.start_time >= self.end_time or rec.end_time <= self.start_time))
            # timetables = timetables.filtered(lambda rec: self.search_filtered(rec))

        timetables = list(timetables)

        key_timetables = {}
        for timetable in timetables:
            if not timetable.date or not timetable.day_of_week or not timetable.employee_id.id:
                continue

            end_time = TimetableFilterWizard.convert_float_to_time(timetable.end_time, has_second=True)
            start_time = TimetableFilterWizard.convert_float_to_time(timetable.start_time, has_second=True)
            if self.print_type == 'teacher':
                key = '{}-{}-{}-{}'.format(timetable.employee_id.id, timetable.date, start_time, end_time)
            else:
                key = '{}-{}-{}-{}'.format(timetable.class_id.id, timetable.date, start_time, end_time)
            if key not in key_timetables:
                key_timetables[key] = {}
                key_timetables[key]['timetable'] = timetable
            else:
                continue

            end_time = TimetableFilterWizard.convert_float_to_time(timetable.end_time, has_second=True)
            start_time = TimetableFilterWizard.convert_float_to_time(timetable.start_time, has_second=True)
            end_time = datetime.strptime(f"{timetable.date} {end_time}", DATETIME_FORMAT)
            start_time = datetime.strptime(f"{timetable.date} {start_time}", DATETIME_FORMAT)

            worked_hours = end_time - start_time
            worked_hours = worked_hours.total_seconds() / 3600.0
            worked_hours = round(worked_hours, 2)

            if worked_hours < 0.0:
                del(key_timetables[key])
                continue

            key_timetables[key]['worked_hours'] = worked_hours

        key_timetable_percentages = {}
        for key in key_timetables.keys():
            if self.print_type == 'teacher':
                k = '{}'.format(key_timetables[key]['timetable'].employee_id.id)
                if k not in key_timetable_percentages:
                    key_timetable_percentages[k] = {}
                    key_timetable_percentages[k]['id'] = key_timetables[key]['timetable'].employee_id.id
                    key_timetable_percentages[k]['name'] = key_timetables[key]['timetable'].employee_id.name
                    key_timetable_percentages[k]['data'] = []
                    key_timetable_percentages[k]['worked_time'] = 0.0
                    key_timetable_percentages[k]['percentage'] = 0.0
            elif self.print_type == 'specialty':
                k = '{}'.format(key_timetables[key]['timetable'].specialty_id.id)
                if k not in key_timetable_percentages:
                    key_timetable_percentages[k] = {}
                    key_timetable_percentages[k]['id'] = key_timetables[key]['timetable'].specialty_id.id
                    key_timetable_percentages[k]['name'] = '{} ({})'.format(key_timetables[key]['timetable'].specialty_id.name, key_timetables[key]['timetable'].specialty_id.field_of_study_id.cycle_id.name)
                    key_timetable_percentages[k]['data'] = []
                    key_timetable_percentages[k]['worked_time'] = 0.0
                    key_timetable_percentages[k]['percentage'] = 0.0
            elif self.print_type == 'department':
                k = '{}'.format(key_timetables[key]['timetable'].department_id.id)
                if k not in key_timetable_percentages:
                    key_timetable_percentages[k] = {}
                    key_timetable_percentages[k]['id'] = key_timetables[key]['timetable'].department_id.id
                    key_timetable_percentages[k]['name'] = key_timetables[key]['timetable'].department_id.name
                    key_timetable_percentages[k]['data'] = []
                    key_timetable_percentages[k]['worked_time'] = 0.0
                    key_timetable_percentages[k]['percentage'] = 0.0
            else:
                k = '{}'.format(key_timetables[key]['timetable'].school_id.id)
                if k not in key_timetable_percentages:
                    key_timetable_percentages[k] = {}
                    key_timetable_percentages[k]['id'] = key_timetables[key]['timetable'].school_id.id
                    key_timetable_percentages[k]['name'] = key_timetables[key]['timetable'].school_id.name
                    key_timetable_percentages[k]['data'] = []
                    key_timetable_percentages[k]['worked_time'] = 0.0
                    key_timetable_percentages[k]['percentage'] = 0.0
            timetable_percentage = {}
            timetable_percentage['id'] = key_timetables[key]['timetable'].id
            timetable_percentage['date'] = key_timetables[key]['timetable'].date
            timetable_percentage['date_of_week'] = datetime.strftime(key_timetables[key]['timetable'].date, DATE_FORMAT_FR)
            timetable_percentage['class_id'] = key_timetables[key]['timetable'].class_id.id
            timetable_percentage['class_name'] = key_timetables[key]['timetable'].class_id.name
            timetable_percentage['level_id'] = key_timetables[key]['timetable'].level_id.id
            timetable_percentage['level_name'] = key_timetables[key]['timetable'].level_id.name
            timetable_percentage['subject_id'] = key_timetables[key]['timetable'].subject_id.id
            timetable_percentage['subject_name'] = key_timetables[key]['timetable'].subject_id.name
            timetable_percentage['subject_code'] = key_timetables[key]['timetable'].subject_id.code
            timetable_percentage['subject_shared_subject'] = '(TC)' if key_timetables[key]['timetable'].subject_id.shared_subject else ''
            timetable_percentage['employee_id'] = key_timetables[key]['timetable'].employee_id.id
            timetable_percentage['identifier'] = key_timetables[key]['timetable'].employee_id.identifier
            timetable_percentage['employee_name'] = key_timetables[key]['timetable'].employee_id.name
            timetable_percentage['start_time'] = TimetableFilterWizard.convert_float_to_time(key_timetables[key]['timetable'].start_time)
            timetable_percentage['end_time'] = TimetableFilterWizard.convert_float_to_time(key_timetables[key]['timetable'].end_time)
            timetable_percentage['day_of_week'] = CURRENT_WEEKDAY[key_timetables[key]['timetable'].day_of_week]
            timetable_percentage['worked_start_time'] = TimetableFilterWizard.convert_float_to_time(key_timetables[key]['timetable'].worked_start_time)
            timetable_percentage['worked_end_time'] = TimetableFilterWizard.convert_float_to_time(key_timetables[key]['timetable'].worked_end_time)
            timetable_percentage['worked_time'] = key_timetables[key]['worked_hours']
            timetable_percentage['status'] = STATUS_TIMETABLE[key_timetables[key]['timetable'].status]
            key_timetable_percentages[k]['worked_time'] += timetable_percentage['worked_time']
            key_timetable_percentages[k]['data'].append(timetable_percentage)

        for key in key_timetable_percentages.keys():
            key_timetable_percentages[key]['worked_time'] = round(key_timetable_percentages[key]['worked_time'], 2)

        key_all_timetables = {}
        for timetable in all_timetables:
            if not timetable.date or not timetable.day_of_week or not timetable.employee_id.id:
                continue

            end_time = TimetableFilterWizard.convert_float_to_time(timetable.end_time, has_second=True)
            start_time = TimetableFilterWizard.convert_float_to_time(timetable.start_time, has_second=True)
            if self.print_type == 'teacher':
                key = '{}-{}-{}-{}'.format(timetable.employee_id.id, timetable.date, start_time, end_time)
            else:
                key = '{}-{}-{}-{}'.format(timetable.class_id.id, timetable.date, start_time, end_time)
            if key not in key_all_timetables:
                key_all_timetables[key] = {}
                key_all_timetables[key]['timetable'] = timetable
            else:
                continue

            end_time = TimetableFilterWizard.convert_float_to_time(timetable.end_time, has_second=True)
            start_time = TimetableFilterWizard.convert_float_to_time(timetable.start_time, has_second=True)
            end_time = datetime.strptime(f"{timetable.date} {end_time}", DATETIME_FORMAT)
            start_time = datetime.strptime(f"{timetable.date} {start_time}", DATETIME_FORMAT)

            worked_hours = end_time - start_time
            worked_hours = worked_hours.total_seconds() / 3600.0
            worked_hours = round(worked_hours, 2)

            if worked_hours < 0.0:
                del(key_all_timetables[key])
                continue

            key_all_timetables[key]['worked_hours'] = worked_hours

        key_all_timetable_percentages = {}
        for key in key_all_timetables.keys():
            if self.print_type == 'teacher':
                k = '{}'.format(key_all_timetables[key]['timetable'].employee_id.id)
                if k not in key_all_timetable_percentages:
                    key_all_timetable_percentages[k] = {}
                    key_all_timetable_percentages[k]['id'] = key_all_timetables[key]['timetable'].employee_id.id
                    key_all_timetable_percentages[k]['name'] = key_all_timetables[key]['timetable'].employee_id.name
                    key_all_timetable_percentages[k]['data'] = []
                    key_all_timetable_percentages[k]['worked_time'] = 0.0
                    key_all_timetable_percentages[k]['percentage'] = 0.0
            elif self.print_type == 'specialty':
                k = '{}'.format(key_all_timetables[key]['timetable'].specialty_id.id)
                if k not in key_all_timetable_percentages:
                    key_all_timetable_percentages[k] = {}
                    key_all_timetable_percentages[k]['id'] = key_all_timetables[key]['timetable'].specialty_id.id
                    key_all_timetable_percentages[k]['name'] = '{} ({})'.format(key_all_timetables[key]['timetable'].specialty_id.name, key_all_timetables[key]['timetable'].specialty_id.field_of_study_id.cycle_id.name)
                    key_all_timetable_percentages[k]['data'] = []
                    key_all_timetable_percentages[k]['worked_time'] = 0.0
                    key_all_timetable_percentages[k]['percentage'] = 0.0
            elif self.print_type == 'department':
                k = '{}'.format(key_all_timetables[key]['timetable'].department_id.id)
                if k not in key_all_timetable_percentages:
                    key_all_timetable_percentages[k] = {}
                    key_all_timetable_percentages[k]['id'] = key_all_timetables[key]['timetable'].department_id.id
                    key_all_timetable_percentages[k]['name'] = key_all_timetables[key]['timetable'].department_id.name
                    key_all_timetable_percentages[k]['data'] = []
                    key_all_timetable_percentages[k]['worked_time'] = 0.0
                    key_all_timetable_percentages[k]['percentage'] = 0.0
            else:
                k = '{}'.format(key_all_timetables[key]['timetable'].school_id.id)
                if k not in key_all_timetable_percentages:
                    key_all_timetable_percentages[k] = {}
                    key_all_timetable_percentages[k]['id'] = key_all_timetables[key]['timetable'].school_id.id
                    key_all_timetable_percentages[k]['name'] = key_all_timetables[key]['timetable'].school_id.name
                    key_all_timetable_percentages[k]['data'] = []
                    key_all_timetable_percentages[k]['worked_time'] = 0.0
                    key_all_timetable_percentages[k]['percentage'] = 0.0
            timetable_percentage = {}
            timetable_percentage['id'] = key_all_timetables[key]['timetable'].id
            timetable_percentage['date'] = key_all_timetables[key]['timetable'].date
            timetable_percentage['date_of_week'] = datetime.strftime(key_all_timetables[key]['timetable'].date, DATE_FORMAT_FR)
            timetable_percentage['class_id'] = key_all_timetables[key]['timetable'].class_id.id
            timetable_percentage['class_name'] = key_all_timetables[key]['timetable'].class_id.name
            timetable_percentage['level_id'] = key_all_timetables[key]['timetable'].level_id.id
            timetable_percentage['level_name'] = key_all_timetables[key]['timetable'].level_id.name
            timetable_percentage['subject_id'] = key_all_timetables[key]['timetable'].subject_id.id
            timetable_percentage['subject_name'] = key_all_timetables[key]['timetable'].subject_id.name
            timetable_percentage['subject_code'] = key_all_timetables[key]['timetable'].subject_id.code
            timetable_percentage['subject_shared_subject'] = '(TC)' if key_all_timetables[key]['timetable'].subject_id.shared_subject else ''
            timetable_percentage['employee_id'] = key_all_timetables[key]['timetable'].employee_id.id
            timetable_percentage['identifier'] = key_all_timetables[key]['timetable'].employee_id.identifier
            timetable_percentage['employee_name'] = key_all_timetables[key]['timetable'].employee_id.name
            timetable_percentage['start_time'] = TimetableFilterWizard.convert_float_to_time(key_all_timetables[key]['timetable'].start_time)
            timetable_percentage['end_time'] = TimetableFilterWizard.convert_float_to_time(key_all_timetables[key]['timetable'].end_time)
            timetable_percentage['day_of_week'] = CURRENT_WEEKDAY[key_all_timetables[key]['timetable'].day_of_week]
            timetable_percentage['worked_start_time'] = TimetableFilterWizard.convert_float_to_time(key_all_timetables[key]['timetable'].worked_start_time)
            timetable_percentage['worked_end_time'] = TimetableFilterWizard.convert_float_to_time(key_all_timetables[key]['timetable'].worked_end_time)
            timetable_percentage['worked_time'] = key_all_timetables[key]['worked_hours']
            timetable_percentage['status'] = STATUS_TIMETABLE[key_all_timetables[key]['timetable'].status]
            key_all_timetable_percentages[k]['worked_time'] += timetable_percentage['worked_time']
            key_all_timetable_percentages[k]['data'].append(timetable_percentage)

        for key in key_all_timetable_percentages.keys():
            key_all_timetable_percentages[key]['worked_time'] = round(key_all_timetable_percentages[key]['worked_time'], 2)

        for key in key_timetable_percentages.keys():
            if key in key_all_timetable_percentages:
                worked_time = key_timetable_percentages[key]['worked_time']
                if key_all_timetable_percentages[key]['worked_time'] > 0:
                    key_timetable_percentages[key]['percentage'] = (worked_time / key_all_timetable_percentages[key]['worked_time']) * 100
                    key_timetable_percentages[key]['percentage'] = round(key_timetable_percentages[key]['percentage'], 2)

        key_timetable_percentages = sorted(key_timetable_percentages.items(), key=self.sort_timetable_percentage, reverse=True)
        key_timetable_percentages = dict(key_timetable_percentages)

        _logger.info(f'----------- tototototototo key_timetable_percentages {key_timetable_percentages} -----------')

        if len(title) > 0:
            title = ' / '.join(title)
        else:
            title = 'Non spécifié'

        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', title)

        filter_title = self.env['ir.config_parameter'].sudo().get_param(f'siantou.filter_user_{self.env.user.id}', '')

        if self.print_type == 'teacher':
            label = 'Enseignant'
        elif self.print_type == 'specialty':
            label = 'Spécialité'
        elif self.print_type == 'department':
            label = 'Département'
        else:
            label = 'École'

        title = 'Pourcentage d\'heures par {}'.format(label)

        if not self.is_permanent or not self.is_temporary:
            if self.is_permanent:
                title = 'Pourcentage d\'heures permanent par {}'.format(label)
            if self.is_temporary:
                title = 'Pourcentage d\'heures vacataire par {}'.format(label)

        data = {
            'docdata': {}
        }
        data['docdata']['label'] = label
        data['docdata']['title'] = title
        data['docdata']['filter'] = filter_title
        data['docdata']['timetable_percentage_data'] = key_timetable_percentages

        if self.school_id.id:
            data['docdata']['title'] = '{} {}'.format(data['docdata']['title'], self.school_id.name)

        start_date = datetime.strftime(self.start_date, DATE_FORMAT_FR)
        end_date = datetime.strftime(self.end_date, DATE_FORMAT_FR)

        if len(data['docdata']['timetable_percentage_data'].keys()) == 0:
            raise UserError('Aucune donnée trouvée')
        report_action = self.env.ref('siantou_ems_core.action_report_timetable_hours_percentage')
        report_action.update({
            'name': '{} du {} - {} PDF'.format(title, start_date, end_date),
        })
        return report_action.report_action(self, data=data)

    def action_print_hours_and_cost_pdf(self):
        domain = []
        title = []
        if self.year_id.id:
            domain.append(('year_id', '=', self.year_id.id))
            title.append(self.year_id.name)
        if self.semester_id.id:
            domain.append(('semester_id', '=', self.semester_id.id))
            title.append(self.semester_id.name)
        if self.school_id.id:
            domain.append(('school_id', '=', self.school_id.id))
            title.append(self.school_id.name)
        if self.department_id.id:
            domain.append(('department_id', '=', self.department_id.id))
            title.append(self.department_id.name)
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
        if self.class_group_id.id:
            domain.append(('class_group_id', '=', self.class_group_id.id))
            title.append(self.class_group_id.name)
        if self.subject_id.id:
            domain.append(('subject_id', '=', self.subject_id.id))
            title.append(self.subject_id.name)
        if self.building_id.id:
            domain.append(('building_id', '=', self.building_id.id))
            title.append(self.building_id.name)
        if self.classroom_id.id:
            domain.append(('classroom_id', '=', self.classroom_id.id))
            title.append(self.classroom_id.name)
        domain.append(('employee_id.is_teacher', '=', True))
        if not self.is_permanent or not self.is_temporary:
            if self.is_permanent:
                domain.append(('employee_id.is_permanent', '=', True))
                title.append('Est un permanent')
            if self.is_temporary:
                domain.append(('employee_id.is_permanent', '=', False))
                title.append('Est un vacataire')
        if self.employee_id.id:
            domain.append(('employee_id', '=', self.employee_id.id))
            title.append(self.employee_id.name)
        if self.group_id.id:
            domain.append(('group_id', '=', self.group_id.id))
            title.append(self.group_id.name)
        else:
            group_ids = self.env['siantou.ems.timetable.group'].search(['|', '|', ('create_uid', '=', self.env.user.id), ('read_user_ids', '=', self.env.user.id), ('write_user_ids', '=', self.env.user.id)])
            domain.append(('group_id', 'in', group_ids.ids))

        order = 'date asc, id asc'

        timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))

        if self.start_date and self.end_date:
            start_date = datetime.strftime(self.start_date, DATE_FORMAT_FR)
            end_date = datetime.strftime(self.end_date, DATE_FORMAT_FR)
            title.append('{} - {}'.format(start_date, end_date))
            timetables = timetables.filtered(lambda rec: rec.date and rec.day_of_week and rec.date >= self.start_date and rec.date <= self.end_date)
        if self.start_time and self.end_time:
            start_time = TimetableFilterWizard.convert_float_to_time(self.start_time)
            end_time = TimetableFilterWizard.convert_float_to_time(self.end_time)
            title.append('{} - {}'.format(start_time, end_time))
            timetables = timetables.filtered(lambda rec: not (rec.start_time >= self.end_time or rec.end_time <= self.start_time))
            # timetables = timetables.filtered(lambda rec: self.search_filtered(rec))

        timetables = list(timetables)

        key_timetables = {}
        for timetable in timetables:
            if not timetable.date or not timetable.day_of_week or not timetable.employee_id.id:
                continue

            end_time = TimetableFilterWizard.convert_float_to_time(timetable.end_time, has_second=True)
            start_time = TimetableFilterWizard.convert_float_to_time(timetable.start_time, has_second=True)
            if self.print_type == 'teacher':
                key = '{}-{}-{}-{}'.format(timetable.employee_id.id, timetable.date, start_time, end_time)
            else:
                key = '{}-{}-{}-{}'.format(timetable.class_id.id, timetable.date, start_time, end_time)
            if key not in key_timetables:
                key_timetables[key] = {}
                key_timetables[key]['timetable'] = timetable
            else:
                continue

            end_time = TimetableFilterWizard.convert_float_to_time(timetable.end_time, has_second=True)
            start_time = TimetableFilterWizard.convert_float_to_time(timetable.start_time, has_second=True)
            end_time = datetime.strptime(f"{timetable.date} {end_time}", DATETIME_FORMAT)
            start_time = datetime.strptime(f"{timetable.date} {start_time}", DATETIME_FORMAT)

            worked_hours = end_time - start_time
            worked_hours = worked_hours.total_seconds() / 3600.0
            worked_hours = round(worked_hours, 2)

            if worked_hours < 0.0:
                del(key_timetables[key])
                continue

            if len(timetable.employee_id.diplome_ids.ids) > 0:
                domain = [
                    ('school_id', '=', timetable.school_id.id),
                    ('cycle_id', '=', timetable.cycle_id.id),
                    ('level_id', '=', timetable.level_id.id),
                    ('type_cour', '=', timetable.type_cour),
                    ('diplome_availability_id.diplome_ids', 'in', timetable.employee_id.diplome_ids.ids),
                ]
            else:
                domain = [
                    ('school_id', '=', timetable.school_id.id),
                    ('cycle_id', '=', timetable.cycle_id.id),
                    ('level_id', '=', timetable.level_id.id),
                    ('type_cour', '=', timetable.type_cour),
                ]

            hourly_rates = self.env['siantou.ems.core.hourly.rate'].search(domain)
            hourly_rates = list(hourly_rates)

            min_hourly_rate = None
            min_teacher_hourly_rate = None
            if len(hourly_rates) > 0:
                for hourly_rate in hourly_rates:
                    domain = [
                        ('hourly_rate_id', '=', hourly_rate.id),
                        ('employee_id', '=', timetable.employee_id.id),
                    ]

                    teacher_hourly_rates = self.env['siantou.ems.core.teacher.hourly.rate'].search(domain, limit=1)
                    teacher_hourly_rates = list(teacher_hourly_rates)
                    if len(teacher_hourly_rates) > 0:
                        for teacher_hourly_rate in teacher_hourly_rates:
                            if not min_teacher_hourly_rate:
                                min_teacher_hourly_rate = teacher_hourly_rate.rate
                            else:
                                if teacher_hourly_rate.rate < min_teacher_hourly_rate:
                                    min_teacher_hourly_rate = teacher_hourly_rate.rate
                    if not min_hourly_rate:
                        min_hourly_rate = hourly_rate.rate
                    else:
                        if hourly_rate.rate < min_hourly_rate:
                            min_hourly_rate = hourly_rate.rate

            if min_teacher_hourly_rate:
                rate = min_teacher_hourly_rate
            elif min_hourly_rate:
                rate = min_hourly_rate
            else:
                rate = 0.0

            amount = rate * worked_hours
            amount = round(amount, 2)

            if timetable.employee_id.is_permanent:
                rate = 0.0
                amount = 0.0

            if not timetable.employee_id.is_permanent:
                if rate == 0.0:
                    del(key_timetables[key])
                    continue

            hours_credit = timetable.subject_id.hours_credit

            key_timetables[key]['rate'] = rate
            key_timetables[key]['amount'] = amount
            key_timetables[key]['worked_hours'] = worked_hours
            key_timetables[key]['hours_credit'] = hours_credit

        key_timetable_hours_and_costs = {}
        for key in key_timetables.keys():
            if self.print_type == 'teacher':
                k = '{}'.format(key_timetables[key]['timetable'].employee_id.id)
                if k not in key_timetable_hours_and_costs:
                    key_timetable_hours_and_costs[k] = {}
                    key_timetable_hours_and_costs[k]['id'] = key_timetables[key]['timetable'].employee_id.id
                    key_timetable_hours_and_costs[k]['name'] = key_timetables[key]['timetable'].employee_id.name
                    key_timetable_hours_and_costs[k]['data'] = []
                    key_timetable_hours_and_costs[k]['worked_time'] = 0.0
                    key_timetable_hours_and_costs[k]['amount'] = 0.0
                    key_timetable_hours_and_costs[k]['total_amount'] = 0.0
            elif self.print_type == 'specialty':
                k = '{}'.format(key_timetables[key]['timetable'].specialty_id.id)
                if k not in key_timetable_hours_and_costs:
                    key_timetable_hours_and_costs[k] = {}
                    key_timetable_hours_and_costs[k]['id'] = key_timetables[key]['timetable'].specialty_id.id
                    key_timetable_hours_and_costs[k]['name'] = '{} ({})'.format(key_timetables[key]['timetable'].specialty_id.name, key_timetables[key]['timetable'].specialty_id.field_of_study_id.cycle_id.name)
                    key_timetable_hours_and_costs[k]['data'] = []
                    key_timetable_hours_and_costs[k]['worked_time'] = 0.0
                    key_timetable_hours_and_costs[k]['amount'] = 0.0
                    key_timetable_hours_and_costs[k]['total_amount'] = 0.0
            elif self.print_type == 'department':
                k = '{}'.format(key_timetables[key]['timetable'].department_id.id)
                if k not in key_timetable_hours_and_costs:
                    key_timetable_hours_and_costs[k] = {}
                    key_timetable_hours_and_costs[k]['id'] = key_timetables[key]['timetable'].department_id.id
                    key_timetable_hours_and_costs[k]['name'] = key_timetables[key]['timetable'].department_id.name
                    key_timetable_hours_and_costs[k]['data'] = []
                    key_timetable_hours_and_costs[k]['worked_time'] = 0.0
                    key_timetable_hours_and_costs[k]['amount'] = 0.0
                    key_timetable_hours_and_costs[k]['total_amount'] = 0.0
            else:
                k = '{}'.format(key_timetables[key]['timetable'].school_id.id)
                if k not in key_timetable_hours_and_costs:
                    key_timetable_hours_and_costs[k] = {}
                    key_timetable_hours_and_costs[k]['id'] = key_timetables[key]['timetable'].school_id.id
                    key_timetable_hours_and_costs[k]['name'] = key_timetables[key]['timetable'].school_id.name
                    key_timetable_hours_and_costs[k]['data'] = []
                    key_timetable_hours_and_costs[k]['worked_time'] = 0.0
                    key_timetable_hours_and_costs[k]['amount'] = 0.0
                    key_timetable_hours_and_costs[k]['total_amount'] = 0.0
            timetable_hours_and_cost = {}
            timetable_hours_and_cost['id'] = key_timetables[key]['timetable'].id
            timetable_hours_and_cost['date'] = key_timetables[key]['timetable'].date
            timetable_hours_and_cost['date_of_week'] = datetime.strftime(key_timetables[key]['timetable'].date, DATE_FORMAT_FR)
            timetable_hours_and_cost['class_id'] = key_timetables[key]['timetable'].class_id.id
            timetable_hours_and_cost['class_name'] = key_timetables[key]['timetable'].class_id.name
            timetable_hours_and_cost['level_id'] = key_timetables[key]['timetable'].level_id.id
            timetable_hours_and_cost['level_name'] = key_timetables[key]['timetable'].level_id.name
            timetable_hours_and_cost['subject_id'] = key_timetables[key]['timetable'].subject_id.id
            timetable_hours_and_cost['subject_name'] = key_timetables[key]['timetable'].subject_id.name
            timetable_hours_and_cost['subject_code'] = key_timetables[key]['timetable'].subject_id.code
            timetable_hours_and_cost['subject_shared_subject'] = '(TC)' if key_timetables[key]['timetable'].subject_id.shared_subject else ''
            timetable_hours_and_cost['employee_id'] = key_timetables[key]['timetable'].employee_id.id
            timetable_hours_and_cost['identifier'] = key_timetables[key]['timetable'].employee_id.identifier
            timetable_hours_and_cost['employee_name'] = key_timetables[key]['timetable'].employee_id.name
            timetable_hours_and_cost['start_time'] = TimetableFilterWizard.convert_float_to_time(key_timetables[key]['timetable'].start_time)
            timetable_hours_and_cost['end_time'] = TimetableFilterWizard.convert_float_to_time(key_timetables[key]['timetable'].end_time)
            timetable_hours_and_cost['day_of_week'] = CURRENT_WEEKDAY[key_timetables[key]['timetable'].day_of_week]
            timetable_hours_and_cost['worked_start_time'] = TimetableFilterWizard.convert_float_to_time(key_timetables[key]['timetable'].worked_start_time)
            timetable_hours_and_cost['worked_end_time'] = TimetableFilterWizard.convert_float_to_time(key_timetables[key]['timetable'].worked_end_time)
            timetable_hours_and_cost['worked_time'] = key_timetables[key]['worked_hours']
            timetable_hours_and_cost['rate'] = key_timetables[key]['rate']
            timetable_hours_and_cost['amount'] = key_timetables[key]['amount']
            timetable_hours_and_cost['hours_credit'] = key_timetables[key]['hours_credit']
            timetable_hours_and_cost['status'] = STATUS_TIMETABLE[key_timetables[key]['timetable'].status]
            key_timetable_hours_and_costs[k]['worked_time'] += timetable_hours_and_cost['worked_time']
            key_timetable_hours_and_costs[k]['amount'] += timetable_hours_and_cost['amount']
            key_timetable_hours_and_costs[k]['total_amount'] = key_timetable_hours_and_costs[k]['amount']
            key_timetable_hours_and_costs[k]['data'].append(timetable_hours_and_cost)

        total_hours = 0.0
        total_cost = 0.0
        for key in key_timetable_hours_and_costs.keys():
            key_timetable_hours_and_costs[key]['worked_time'] = round(key_timetable_hours_and_costs[key]['worked_time'], 2)
            key_timetable_hours_and_costs[key]['amount'] = round(key_timetable_hours_and_costs[key]['amount'], 2)
            total_hours += key_timetable_hours_and_costs[key]['worked_time']
            total_cost += key_timetable_hours_and_costs[key]['amount']
        total_hours = round(total_hours, 2)
        total_cost = round(total_cost, 2)

        key_timetable_hours_and_costs = sorted(key_timetable_hours_and_costs.items(), key=self.sort_timetable_hours, reverse=True)
        key_timetable_hours_and_costs = dict(key_timetable_hours_and_costs)

        _logger.info(f'----------- tototototototo key_timetable_hours_and_costs {key_timetable_hours_and_costs} -----------')

        if len(title) > 0:
            title = ' / '.join(title)
        else:
            title = 'Non spécifié'

        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', title)

        filter_title = self.env['ir.config_parameter'].sudo().get_param(f'siantou.filter_user_{self.env.user.id}', '')

        if self.print_type == 'teacher':
            label = 'Enseignant'
        elif self.print_type == 'specialty':
            label = 'Spécialité'
        elif self.print_type == 'department':
            label = 'Département'
        else:
            label = 'École'

        title = 'Nombre d\'heures et coût par {}'.format(label)

        if not self.is_permanent or not self.is_temporary:
            if self.is_permanent:
                title = 'Nombre d\'heures et coût permanent par {}'.format(label)
            if self.is_temporary:
                title = 'Nombre d\'heures et coût vacataire par {}'.format(label)

        is_permanent = False
        if not self.is_permanent or not self.is_temporary:
            if self.is_permanent:
                is_permanent = True

        data = {
            'docdata': {}
        }
        data['docdata']['label'] = label
        data['docdata']['title'] = title
        data['docdata']['filter'] = filter_title
        data['docdata']['timetable_hours_and_cost_data'] = key_timetable_hours_and_costs
        data['docdata']['total_hours'] = total_hours
        data['docdata']['total_cost'] = total_cost
        data['docdata']['is_permanent'] = is_permanent

        if self.school_id.id:
            data['docdata']['title'] = '{} {}'.format(data['docdata']['title'], self.school_id.name)

        start_date = datetime.strftime(self.start_date, DATE_FORMAT_FR)
        end_date = datetime.strftime(self.end_date, DATE_FORMAT_FR)

        if len(data['docdata']['timetable_hours_and_cost_data'].keys()) == 0:
            raise UserError('Aucune donnée trouvée')
        report_action = self.env.ref('siantou_ems_core.action_report_timetable_hours_and_cost')
        report_action.update({
            'name': '{} du {} - {} PDF'.format(title, start_date, end_date),
        })
        return report_action.report_action(self, data=data)

    @staticmethod
    def convert_float_to_time(tm, has_second=False):
        tm = str(tm)
        tm = tm.split('.')
        if len(tm) == 1:
            tm.append('0')
        if len(tm[0]) == 1:
            tm[0] = '0{}'.format(tm[0])
        elif len(tm[0]) > 2:
            tm[0] = '{}'.format(tm[0][0:2])
        if int(tm[0]) > 23:
            tm[0] = '00'
        if len(tm[1]) == 1:
            tm[1] = '{}0'.format(tm[1])
        elif len(tm[1]) > 2:
            tm[1] = '{}'.format(tm[1][0:2])
        if int(tm[1]) > 59:
            tm[1] = '00'
        tm = ':'.join(tm)
        if has_second:
            tm = '{}:00'.format(tm)
        return tm

    @staticmethod
    def compare_float_time(date_time, first_time, second_time):
        first_time = datetime.strptime(f"{date_time} {TimetableFilterWizard.convert_float_to_time(first_time, has_second=True)}", DATETIME_FORMAT)
        second_time = datetime.strptime(f"{date_time} {TimetableFilterWizard.convert_float_to_time(second_time, has_second=True)}", DATETIME_FORMAT)
        delay_time = first_time - second_time
        delay_time = delay_time.total_seconds() / 60.0
        delay_time = round(delay_time, 2)
        return delay_time
