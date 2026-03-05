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
        required=True
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
        related='specialty_id.department_id',
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

    specialty_id_domain = fields.Binary(compute='_compute_school_domain', default=[])

    subject_id_domain = fields.Binary(compute='_compute_class_domain', default=[])

    class_id_domain = fields.Binary(compute='_compute_all_domain', default=[])

    school_id_domain = fields.Binary(compute='_compute_group_domain', default=[])

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
            record.semester_id = None
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

    @api.depends('group_id', 'school_id')
    def _compute_school_domain(self):
        for record in self:
            department_ids = record.group_id.department_ids
            domain = []
            if record.school_id.id:
                domain.append(('school_id', '=', record.school_id.id))
            if len(department_ids.ids) > 0:
                domain.append(('department_id', 'in', department_ids.ids))
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
        if self.employee_id.id:
            domain.append(('employee_id', '=', self.employee_id.id))
            title.append(self.employee_id.name)
        if self.group_id.id:
            domain.append(('group_id', '=', self.group_id.id))
            title.append(self.group_id.name)
        else:
            group_ids = self.env['siantou.ems.timetable.group'].search(['|', '|', ('create_uid', '=', self.env.user.id), ('read_user_ids', '=', self.env.user.id), ('write_user_ids', '=', self.env.user.id)])
            domain.append(('group_id', 'in', group_ids.ids))

        if self.status:
            if self.status == 'delay':
                domain.append(('status', '=', 'present'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
                timetables = timetables.filtered(lambda rec: rec.date and rec.day_of_week and TimetableFilterWizard.compare_float_time(rec.date, rec.worked_start_time, rec.start_time) > 0.0)
            elif self.status == 'delay_more_than_or_equal':
                domain.append(('status', '=', 'present'))
                title.append(STATUS_TIMETABLE[self.status])
                title.append('{} minute(s)'.format(self.number_of_minute))
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
                timetables = timetables.filtered(lambda rec: rec.date and rec.day_of_week and TimetableFilterWizard.compare_float_time(rec.date, rec.worked_start_time, rec.start_time) >= self.number_of_minute)
            elif self.status == 'delay_less_than':
                domain.append(('status', '=', 'present'))
                title.append(STATUS_TIMETABLE[self.status])
                title.append('{} minute(s)'.format(self.number_of_minute))
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
                timetables = timetables.filtered(lambda rec: rec.date and rec.day_of_week and TimetableFilterWizard.compare_float_time(rec.date, rec.worked_start_time, rec.start_time) > 0.0 and TimetableFilterWizard.compare_float_time(rec.date, rec.worked_start_time, rec.start_time) < self.number_of_minute)
            elif self.status == 'punctuality':
                domain.append(('status', '=', 'present'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
                timetables = timetables.filtered(lambda rec: rec.date and rec.day_of_week and TimetableFilterWizard.compare_float_time(rec.date, rec.worked_start_time, rec.start_time) == 0.0)
            elif self.status == 'exception_start_time_invalid':
                domain.append(('status', '=', 'exception'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
                timetables = timetables.filtered(lambda rec: rec.reason and rec.reason == 'Poinçonnement de début absent ou invalide')
            elif self.status == 'exception_end_time_invalid':
                domain.append(('status', '=', 'exception'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
                timetables = timetables.filtered(lambda rec: rec.reason and rec.reason == 'Poinçonnement de fin absent ou invalide')
            elif self.status == 'exception_time_invalid':
                domain.append(('status', '=', 'exception'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
                timetables = timetables.filtered(lambda rec: rec.reason and rec.reason == 'Poinçonnement absent ou invalide')
            elif self.status == 'exception_reverse':
                domain.append(('status', '=', 'exception'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
                timetables = timetables.filtered(lambda rec: rec.reason and rec.reason == 'Poinçonnement de début et de fin inversé')
            elif self.status == 'exception_other':
                domain.append(('status', '=', 'exception'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
                timetables = timetables.filtered(lambda rec: rec.reason and rec.reason not in ['Poinçonnement de début absent ou invalide', 'Poinçonnement de fin absent ou invalide', 'Poinçonnement absent ou invalide', 'Poinçonnement de début et de fin inversé'])
            else:
                domain.append(('status', '=', self.status))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
        else:
            timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
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

            end_time = TimetableFilterWizard.convert_float_to_time(timetable.end_time, True)
            start_time = TimetableFilterWizard.convert_float_to_time(timetable.start_time, True)
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
            'domain' : domain,
            'target': 'main',
        }

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
        if self.employee_id.id:
            domain.append(('employee_id', '=', self.employee_id.id))
            title.append(self.employee_id.name)
        if self.group_id.id:
            domain.append(('group_id', '=', self.group_id.id))
            title.append(self.group_id.name)
        else:
            group_ids = self.env['siantou.ems.timetable.group'].search(['|', '|', ('create_uid', '=', self.env.user.id), ('read_user_ids', '=', self.env.user.id), ('write_user_ids', '=', self.env.user.id)])
            domain.append(('group_id', 'in', group_ids.ids))

        all_domain = []
        all_domain += domain
        all_domain.append(('status', '!=', 'pending'))
        all_timetables = self.env['siantou.ems.timetable.timetable'].search(all_domain)

        if self.status:
            if self.status == 'delay':
                domain.append(('status', '=', 'present'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
                timetables = timetables.filtered(lambda rec: rec.date and rec.day_of_week and TimetableFilterWizard.compare_float_time(rec.date, rec.worked_start_time, rec.start_time) >= 0.0)
            elif self.status == 'delay_more_than_or_equal':
                domain.append(('status', '=', 'present'))
                title.append(STATUS_TIMETABLE[self.status])
                title.append('{} minute(s)'.format(self.number_of_minute))
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
                timetables = timetables.filtered(lambda rec: rec.date and rec.day_of_week and TimetableFilterWizard.compare_float_time(rec.date, rec.worked_start_time, rec.start_time) >= self.number_of_minute)
            elif self.status == 'delay_less_than':
                domain.append(('status', '=', 'present'))
                title.append(STATUS_TIMETABLE[self.status])
                title.append('{} minute(s)'.format(self.number_of_minute))
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
                timetables = timetables.filtered(lambda rec: rec.date and rec.day_of_week and TimetableFilterWizard.compare_float_time(rec.date, rec.worked_start_time, rec.start_time) > 0.0 and TimetableFilterWizard.compare_float_time(rec.date, rec.worked_start_time, rec.start_time) < self.number_of_minute)
            elif self.status == 'punctuality':
                domain.append(('status', 'in', ['present', 'absent']))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
                timetables = timetables.filtered(lambda rec: rec.date and rec.day_of_week and (rec.status == 'absent' or (rec.status == 'present' and TimetableFilterWizard.compare_float_time(rec.date, rec.worked_start_time, rec.start_time) == 0.0)))
            elif self.status == 'exception_start_time_invalid':
                domain.append(('status', '=', 'exception'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
                timetables = timetables.filtered(lambda rec: rec.reason and rec.reason == 'Poinçonnement de début absent ou invalide')
            elif self.status == 'exception_end_time_invalid':
                domain.append(('status', '=', 'exception'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
                timetables = timetables.filtered(lambda rec: rec.reason and rec.reason == 'Poinçonnement de fin absent ou invalide')
            elif self.status == 'exception_time_invalid':
                domain.append(('status', '=', 'exception'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
                timetables = timetables.filtered(lambda rec: rec.reason and rec.reason == 'Poinçonnement absent ou invalide')
            elif self.status == 'exception_reverse':
                domain.append(('status', '=', 'exception'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
                timetables = timetables.filtered(lambda rec: rec.reason and rec.reason == 'Poinçonnement de début et de fin inversé')
            elif self.status == 'exception_other':
                domain.append(('status', '=', 'exception'))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
                timetables = timetables.filtered(lambda rec: rec.reason and rec.reason not in ['Poinçonnement de début absent ou invalide', 'Poinçonnement de fin absent ou invalide', 'Poinçonnement absent ou invalide', 'Poinçonnement de début et de fin inversé'])
            else:
                domain.append(('status', '=', self.status))
                title.append(STATUS_TIMETABLE[self.status])
                timetables = self.env['siantou.ems.timetable.timetable'].search(domain)
        else:
            timetables = self.env['siantou.ems.timetable.timetable'].search(domain)

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

            end_time = TimetableFilterWizard.convert_float_to_time(timetable.end_time, True)
            start_time = TimetableFilterWizard.convert_float_to_time(timetable.start_time, True)
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

            end_time = TimetableFilterWizard.convert_float_to_time(timetable.end_time, True)
            start_time = TimetableFilterWizard.convert_float_to_time(timetable.start_time, True)
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
        data = report_data.print_timetable_percentage_report_data(domains=domain, all_domains=all_domain, status=self.status, sort_type=sort_type)

        # Appeler le rapport PDF
        if len(data['docdata']['timetable_percentage_data'].keys()) == 0:
            raise UserError('Aucune donnée trouvée')
        if print_percentage:
            start_date = datetime.strftime(self.start_date, DATE_FORMAT_FR)
            end_date = datetime.strftime(self.end_date, DATE_FORMAT_FR)
            report_action = self.env.ref('siantou_ems_core.action_report_timetable_percentage')
            if self.school_id.id:
                report_action.update({
                    'name': '{} {} du {} - {} PDF'.format(STATUS_TIMETABLE[self.status], self.school_id.name, start_date, end_date),
                })
            else:
                report_action.update({
                    'name': '{} du {} - {} PDF'.format(STATUS_TIMETABLE[self.status], start_date, end_date),
                })
            return report_action.report_action(self, data=data)
        else:
            return data

    def action_print_top_percentage_pdf(self):
        start_date = datetime.strftime(self.start_date, DATE_FORMAT_FR)
        end_date = datetime.strftime(self.end_date, DATE_FORMAT_FR)
        data = self.action_print_percentage_pdf(sort_type='top', print_percentage=False)
        report_action = self.env.ref('siantou_ems_core.action_report_timetable_percentage')
        if self.school_id.id:
            report_action.update({
                'name': '{} {} Top 10 du {} - {} PDF'.format(STATUS_TIMETABLE[self.status], self.school_id.name, start_date, end_date),
            })
        else:
            report_action.update({
                'name': '{} Top 10 du {} - {} PDF'.format(STATUS_TIMETABLE[self.status], start_date, end_date),
            })
        return report_action.report_action(self, data=data)

    def action_print_last_percentage_pdf(self):
        start_date = datetime.strftime(self.start_date, DATE_FORMAT_FR)
        end_date = datetime.strftime(self.end_date, DATE_FORMAT_FR)
        data = self.action_print_percentage_pdf(sort_type='last', print_percentage=False)
        report_action = self.env.ref('siantou_ems_core.action_report_timetable_percentage')
        if self.school_id.id:
            report_action.update({
                'name': '{} {} Last 10 du {} - {} PDF'.format(STATUS_TIMETABLE[self.status], self.school_id.name, start_date, end_date),
            })
        else:
            report_action.update({
                'name': '{} Last 10 du {} - {} PDF'.format(STATUS_TIMETABLE[self.status], start_date, end_date),
            })
        return report_action.report_action(self, data=data)

    def sort_type_timetable_percentage(self, timetable_percentage):
        percentage = timetable_percentage[1]['percentage']
        return percentage

    def action_print_school_percentage_pdf(self):
        start_date = datetime.strftime(self.start_date, DATE_FORMAT_FR)
        end_date = datetime.strftime(self.end_date, DATE_FORMAT_FR)
        data = {}
        school_ids = self.env['siantou.ems.core.school'].search([])
        school_ids = list(school_ids)
        for school_id in school_ids:
            try:
                self.school_id = school_id
                key = '{}'.format(school_id.id)
                data[key] = self.action_print_percentage_pdf(print_percentage=False)
                data[key]['docdata']['name'] = school_id.name
            except UserError as error:
                _logger.info(f'----------- tototototototo Exception {error} -----------')

        all_data = {
            'docdata': {}
        }
        for key in data.keys():
            all_data['docdata']['title'] = data[key]['docdata']['title']
            all_data['docdata']['filter'] = data[key]['docdata']['filter']
            all_data['docdata']['sort_type'] = data[key]['docdata']['sort_type']
            all_data['docdata']['status'] = data[key]['docdata']['status']
            if 'timetable_percentage_data' not in all_data['docdata']:
                all_data['docdata']['timetable_percentage_data'] = {}
            all_data['docdata']['timetable_percentage_data'][key] = {}
            all_data['docdata']['timetable_percentage_data'][key]['name'] = data[key]['docdata']['name']
            all_data['docdata']['timetable_percentage_data'][key]['percentage'] = data[key]['docdata']['total_percentage']
            all_data['docdata']['timetable_percentage_data'][key]['class'] = ''

        self.school_id = None

        if self.status and self.status in ['present', 'punctuality']:
            all_data['docdata']['timetable_percentage_data'] = sorted(all_data['docdata']['timetable_percentage_data'].items(), key=self.sort_type_timetable_percentage, reverse=True)
            all_data['docdata']['timetable_percentage_data'] = dict(all_data['docdata']['timetable_percentage_data'])
        else:
            all_data['docdata']['timetable_percentage_data'] = sorted(all_data['docdata']['timetable_percentage_data'].items(), key=self.sort_type_timetable_percentage)
            all_data['docdata']['timetable_percentage_data'] = dict(all_data['docdata']['timetable_percentage_data'])

        for key in all_data['docdata']['timetable_percentage_data'].keys():
            if self.status and self.status in ['present', 'punctuality']:
                if all_data['docdata']['timetable_percentage_data'][key]['percentage'] >= 90.0:
                    all_data['docdata']['timetable_percentage_data'][key]['class'] = 'text-success'
                if all_data['docdata']['timetable_percentage_data'][key]['percentage'] >= 80.0 and all_data['docdata']['timetable_percentage_data'][key]['percentage'] < 90.0:
                    all_data['docdata']['timetable_percentage_data'][key]['class'] = 'text-warning'
                if all_data['docdata']['timetable_percentage_data'][key]['percentage'] < 80.0:
                    all_data['docdata']['timetable_percentage_data'][key]['class'] = 'text-danger'
            else:
                if all_data['docdata']['timetable_percentage_data'][key]['percentage'] < 10.0:
                    all_data['docdata']['timetable_percentage_data'][key]['class'] = 'text-success'
                if all_data['docdata']['timetable_percentage_data'][key]['percentage'] >= 10.0 and all_data['docdata']['timetable_percentage_data'][key]['percentage'] < 20.0:
                    all_data['docdata']['timetable_percentage_data'][key]['class'] = 'text-warning'
                if all_data['docdata']['timetable_percentage_data'][key]['percentage'] >= 20.0:
                    all_data['docdata']['timetable_percentage_data'][key]['class'] = 'text-danger'

        if len(all_data['docdata'].keys()) == 0:
            raise UserError('Aucune donnée trouvée')
        report_action = self.env.ref('siantou_ems_core.action_report_timetable_school_percentage')
        report_action.update({
            'name': '{} du {} - {} PDF'.format(STATUS_TIMETABLE[self.status], start_date, end_date),
        })
        return report_action.report_action(self, data=all_data)

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
            self.start_date = self.start_date - timedelta(weeks=1)
            self.end_date = self.end_date - timedelta(weeks=1)
            key = '{}-{}'.format(self.start_date, self.end_date)
            data[key] = self.action_print_percentage_pdf(print_percentage=False)
        except UserError as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

        all_data = {
            'docdata': {}
        }
        for key in data.keys():
            all_data['docdata']['title'] = data[key]['docdata']['title']
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

        self.end_date = datetime.strptime(end_date, DATE_FORMAT_FR)
        self.start_date = datetime.strptime(start_date, DATE_FORMAT_FR)

        if len(all_data['docdata'].keys()) == 0:
            raise UserError('Aucune donnée trouvée')
        report_action = self.env.ref('siantou_ems_core.action_report_timetable_percentage')
        if self.school_id.id:
            report_action.update({
                'name': '{} {} du {} - {} PDF'.format(STATUS_TIMETABLE[self.status], self.school_id.name, start_date, end_date),
            })
        else:
            report_action.update({
                'name': '{} du {} - {} PDF'.format(STATUS_TIMETABLE[self.status], start_date, end_date),
            })
        return report_action.report_action(self, data=all_data)

    def action_print_hours_and_cost_pdf(self):
        pass

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
        first_time = datetime.strptime(f"{date_time} {TimetableFilterWizard.convert_float_to_time(first_time, True)}", DATETIME_FORMAT)
        second_time = datetime.strptime(f"{date_time} {TimetableFilterWizard.convert_float_to_time(second_time, True)}", DATETIME_FORMAT)
        delay_time = first_time - second_time
        delay_time = delay_time.total_seconds() / 60.0
        delay_time = round(delay_time, 2)
        return delay_time
