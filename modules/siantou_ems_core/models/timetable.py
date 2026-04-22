# -*- coding: utf-8 -*-

import math
from email.policy import default
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
import psycopg2
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import pytz
import re
import logging

UTC_TZ = pytz.utc

DATE_FORMAT = '%Y-%m-%d'
DATE_FORMAT_FR = '%d/%m/%Y'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATETIME_FORMAT_FR = '%d/%m/%Y %H:%M'
TIME_FORMAT = '%H:%M:%S'
TIME_FORMAT_FR = '%H:%M'

_logger = logging.getLogger(__name__)

class TimetableSubjectHour(models.Model):
    _name = 'siantou.ems.timetable.subject.day.hour'
    _description = 'Jour et heure du cours'

    @api.depends('group_id')
    def _compute_start_date(self):
        for record in self:
            if record.group_id:
                record.start_date = record.group_id.semester_id.start_time
            else:
                record.start_date = None

    # Date du jour où le cours sera programmé
    start_date = fields.Date(
        string='Date de début',
        readonly=False,
        compute='_compute_start_date',
        store=True
    )

    @api.depends('group_id')
    def _compute_end_date(self):
        for record in self:
            if record.group_id:
                record.end_date = record.group_id.semester_id.end_time
            else:
                record.end_date = None

    # Date du jour où le cours sera programmé
    end_date = fields.Date(
        string='Date de fin',
        readonly=False,
        compute='_compute_end_date',
        store=True
    )

    # Jour où le cours est programmé
    day_of_week = fields.Selection([
            ('0', 'Lundi'),
            ('1', 'Mardi'),
            ('2', 'Mercredi'),
            ('3', 'Jeudi'),
            ('4', 'Vendredi'),
            ('5', 'Samedi'),
            ('6', 'Dimanche'),
        ],
        'Jour de la semaine',
        compute='_compute_day_of_week',
        store=True
    )

    # Heure de début du cours
    start_time = fields.Float(
        'Heure de début',
        required=True,
        default=0.0,
        ondelete='cascade',
        widget='time'
    )

    # Heure de fin du cours
    end_time = fields.Float(
        'Heure de fin',
        required=True,
        default=0.0,
        ondelete='cascade',
        widget='time'
    )

    group_id = fields.Many2one(
        'siantou.ems.timetable.group',
        string='Version d\'emploi du temps',
        required=True,
        ondelete='cascade'
    )

    timetable_id = fields.Many2one(
        'siantou.ems.timetable.timetable',
        string='Emploi du temps',
        ondelete='cascade'
    )

    not_active_slotitems = fields.Integer(
        string='Créneau horaire inactif',
        default=0,
    )

    status = fields.Selection([
        ('pending', 'En attente'),
        ('progress', 'En cours'),
        ('present', 'Présent'),
        ('absent', 'Absent'),
        ('permission', 'Permission'),
        ('exception', 'Exception'),
        ('delay', 'Retard'),
    ], 'Statut',
        default='pending',
    )

    @api.constrains('start_date', 'end_date')
    def _constrains_date(self):
        for record in self:
            if record.start_date > record.end_date:
                raise ValidationError('La date de fin doit être supérieure ou égale à la date de début')

    @api.depends('start_date')
    def _compute_day_of_week(self):
        for record in self:
            if record.start_date:
                record.day_of_week = str(record.start_date.weekday())
            else:
                record.day_of_week = None

    @api.onchange('start_date')
    def _onchange_day_of_week(self):
        for record in self:
            if record.start_date:
                record.day_of_week = str(record.start_date.weekday())
            else:
                record.day_of_week = None

    @api.constrains('start_time', 'end_time')
    def _constrains_time(self):
        for record in self:
            if record.start_time < 0.0 or record.end_time < 0.0 or record.start_time > 23.59 or record.end_time > 23.59:
                raise ValidationError("Vous devez définir des heures de début et de fin corrects")
            elif record.start_time >= record.end_time:
                raise ValidationError("L'heure de fin du cours doit être supérieure à l'heure de début du cours")

class Timetable(models.Model):
    _name = 'siantou.ems.timetable.timetable'
    _description = 'Emplois du temps'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    name = fields.Char(
        string='Nom',
        compute='_compute_name', store=True,
    )

    def _default_semester(self):
        group = self.env['siantou.ems.timetable.group'].search([('is_active', '=', True)], limit=1)
        if group:
            return group.semester_id
        else:
            return None

    semester_id = fields.Many2one(
        'siantou.ems.core.year.semester',
        string='Semestre',
        # default=_default_semester,
        related='group_id.semester_id',
        store=True
    )

    year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année académique',
        related='semester_id.year_id',
        store=True
    )

    batch_id = fields.Many2one(
        'siantou.ems.core.student.batch',
        string='Lot d\'étudiants'
    )

    school_id = fields.Many2one(
        'siantou.ems.core.school',
        string='École',
        required=True,
        ondelete='cascade'
    )

    level_id = fields.Many2one(
        'siantou.ems.core.level',
        'Niveau',
        required=True,
        ondelete='cascade'
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
        required=True,
        ondelete='cascade'
    )

    option_id = fields.Many2one(
        'siantou.ems.core.option',
        string='Option',
        ondelete='cascade'
    )

    class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe',
        required=True,
        ondelete='cascade'
    )

    type_cour = fields.Selection([
            ('cj', 'Cours du jour'),
            ('cs', 'Cours du soir'),
        ],
        string='Type de cours',
        related='class_id.type_cour',
        store=True,
    )

    ue_id = fields.Many2one(
        'siantou.ems.core.unite.enseignement',
        string='Unité d\'enseignement',
        # required=True,
        ondelete='cascade'
    )

    subject_id = fields.Many2one(
        'siantou.ems.core.subject',
        string='Cours',
        required=True,
        ondelete='cascade'
    )

    is_custom_hours_credit = fields.Boolean(string='Volume horaire personnalisé ?', default=False)

    hours_credit = fields.Float(
        'Volume horaire',
        compute="_compute_hours_credit",
        store=True
    )

    @api.depends('subject_id', 'is_custom_hours_credit')
    def _compute_hours_credit(self):
        for record in self:
            if record.subject_id.id:
                if record.is_custom_hours_credit:
                    record.hours_credit = record.hours_credit
                else:
                    record.hours_credit = record.subject_id.hours_credit
            else:
                if record.is_custom_hours_credit:
                    record.hours_credit = record.hours_credit
                else:
                    record.hours_credit = None

    @api.onchange('subject_id')
    def _onchange_hours_credit(self):
        for record in self:
            if record.subject_id.id:
                if record.is_custom_hours_credit:
                    record.hours_credit = record.hours_credit
                else:
                    record.hours_credit = record.subject_id.hours_credit
            else:
                if record.is_custom_hours_credit:
                    record.hours_credit = record.hours_credit
                else:
                    record.hours_credit = None

    @api.constrains('class_id', 'class_group_id', 'subject_id', 'date', 'hours_credit')
    def _constrains_hours_credit(self):
        for record in self:
            if record.hours_credit > record.subject_id.hours_credit:
                raise ValidationError(f"Le volume horaire hebdomadaire doit être inférieure ou égale au volume horaire semestriel {record.hours_credit} / {record.subject_id.hours_credit}")
            start_date = record.date - timedelta(days=record.date.weekday())
            end_date = start_date + timedelta(days=6)
            if record.class_group_id.id:
                timetables = self.env['siantou.ems.timetable.timetable'].search([
                    ('id', '!=', record.id),
                    ('class_id', '=', record.class_id.id),
                    ('subject_id', '=', record.subject_id.id),
                    ('class_group_id', '=', record.class_group_id.id),
                ]).filtered(lambda rec: rec.date and rec.day_of_week and rec.date >= start_date and rec.date <= end_date)
            else:
                timetables = self.env['siantou.ems.timetable.timetable'].search([
                    ('id', '!=', record.id),
                    ('class_id', '=', record.class_id.id),
                    ('subject_id', '=', record.subject_id.id),
                    ('class_group_id', '=', False),
                ]).filtered(lambda rec: rec.date and rec.day_of_week and rec.date >= start_date and rec.date <= end_date)
            timetables = list(timetables)
            if len(timetables) > 0:
                total_hours_credit = 0.0
                key_timetables = {}
                for timetable in timetables:
                    if not timetable.date or not timetable.day_of_week or not timetable.employee_id.id:
                        continue

                    end_time = Timetable.convert_float_to_time(timetable.end_time, has_second=True)
                    start_time = Timetable.convert_float_to_time(timetable.start_time, has_second=True)
                    key = '{}-{}-{}-{}'.format(timetable.class_id.id, timetable.date, start_time, end_time)
                    if key not in key_timetables:
                        key_timetables[key] = {}
                        key_timetables[key]['timetable'] = timetable
                    else:
                        continue

                    total_hours_credit += key_timetables[key]['timetable'].hours_credit

                total_hours_credit += record.hours_credit

                if total_hours_credit > record.subject_id.hours_credit:
                    raise ValidationError(f"La somme des volumes horaires hebdomadaires doit être inférieure ou égale au volume horaire semestriel {total_hours_credit} / {record.subject_id.hours_credit}")

    # Bâtiment auquel appartient la salle de classe
    building_id = fields.Many2one(
        'siantou.ems.core.building',
        'Bâtiment',
        required=True,
        ondelete='cascade'
    )

    # Salle liée à la programmation de cours
    classroom_id = fields.Many2one(
        'siantou.ems.core.building.classroom',
        'Salle de classe',
        required=True,
        ondelete='cascade'
    )

    # Enseignant lié à la programmation de cours
    employee_id = fields.Many2one(
        'hr.employee',
        'Enseignant',
        ondelete='cascade'
    )

    def _default_date(self):
        group = self.env['siantou.ems.timetable.group'].search([('is_active', '=', True)], limit=1)
        if group:
            return group.semester_id.start_time
        else:
            return None

    # Date du jour où le cours sera programmé
    date = fields.Date(
        string='Date du jour',
        required=True,
        default=_default_date,
    )

    # Jour où le cours est programmé
    day_of_week = fields.Selection([
            ('0', 'Lundi'),
            ('1', 'Mardi'),
            ('2', 'Mercredi'),
            ('3', 'Jeudi'),
            ('4', 'Vendredi'),
            ('5', 'Samedi'),
            ('6', 'Dimanche'),
        ],
        'Jour de la semaine',
        compute='_compute_day_of_week',
        store=True
    )

    # Heure de début du cours
    start_time = fields.Float(
        'Heure de début',
        required=True,
        default=0.0,
        ondelete='cascade',
        widget='time'
    )

    # Heure de fin du cours
    end_time = fields.Float(
        'Heure de fin',
        required=True,
        default=0.0,
        ondelete='cascade',
        widget='time'
    )

    # Heure de début du cours
    worked_start_time = fields.Float(
        'Heure de début effectuée',
        default=0.0,
        widget='time'
    )

    # Heure de fin du cours
    worked_end_time = fields.Float(
        'Heure de fin effectuée',
        default=0.0,
        widget='time'
    )

    @api.depends('date', 'start_time')
    def _compute_start_datetime(self):
        for record in self:
            if record.date and record.start_time:
                start_time = Timetable.convert_float_to_time(record.start_time, has_second=True)
                datetime_from = datetime.strptime(f"{record.date} {start_time}", DATETIME_FORMAT)
                record.start_datetime = datetime_from
            else:
                record.start_datetime = None

    @api.onchange('date', 'start_time')
    def _onchange_start_datetime(self):
        for record in self:
            if record.date and record.start_time:
                start_time = Timetable.convert_float_to_time(record.start_time, has_second=True)
                datetime_from = datetime.strptime(f"{record.date} {start_time}", DATETIME_FORMAT)
                record.start_datetime = datetime_from
            else:
                record.start_datetime = None

    @api.depends('date', 'end_time')
    def _compute_end_datetime(self):
        for record in self:
            if record.date and record.end_time:
                end_time = Timetable.convert_float_to_time(record.end_time, has_second=True)
                datetime_to = datetime.strptime(f"{record.date} {end_time}", DATETIME_FORMAT)
                record.end_datetime = datetime_to
            else:
                record.end_datetime = None

    @api.onchange('date', 'end_time')
    def _onchange_end_datetime(self):
        for record in self:
            if record.date and record.end_time:
                end_time = Timetable.convert_float_to_time(record.end_time, has_second=True)
                datetime_to = datetime.strptime(f"{record.date} {end_time}", DATETIME_FORMAT)
                record.end_datetime = datetime_to
            else:
                record.end_datetime = None

    # Date et heure de début du cours
    start_datetime = fields.Datetime(
        string='Date et heure de début',
        compute='_compute_start_datetime',
        store=False
    )

    # Date et heure de fin du cours
    end_datetime = fields.Datetime(
        string='Date et heure de fin',
        compute='_compute_end_datetime',
        store=False
    )

    # Heure de fin du cours
    worked_time = fields.Float(
        'Heure effectuée',
        default=0.0,
        # compute='_compute_worked_time',
        # store=False
    )

    # Taux de l\'enseignant
    rate = fields.Float(
        'Taux horaire',
        default=0.0,
    )

    amount = fields.Float(
        'Montant',
        default=0.0,
    )

    def _default_group(self):
        return self.env['siantou.ems.timetable.group'].search([('is_active', '=', True)], limit=1)

    group_id = fields.Many2one(
        'siantou.ems.timetable.group',
        string='Version d\'emploi du temps',
        required=True,
        # default=_default_group,
        ondelete='cascade'
    )

    group_parent_id = fields.Many2one(
        'siantou.ems.timetable.group',
        string='Version d\'emploi du temps parent',
        related='group_id.group_parent_id',
        store=True
    )

    group_child_id = fields.Many2one(
        'siantou.ems.timetable.group',
        string='Version d\'emploi du temps soumise',
        domain="[('is_submit', '=', True), ('semester_id', '=', semester_id), ('status', '=', 'valid')]",
    )

    is_readonly = fields.Boolean(string='Lecture unique ?', compute='_compute_readonly', store=False)

    @api.depends('group_id')
    def _compute_readonly(self):
        for record in self:
            current_date = date.today()
            if record.group_id.id:
                if record.group_id.create_uid.id == self.env.user.id:
                    record.is_readonly = False
                else:
                    if self.env.user.id in record.group_id.write_user_ids.ids:
                        if record.group_id.start_date > current_date or record.group_id.end_date <= current_date:
                            record.is_readonly = True
                        else:
                            record.is_readonly = False
                    else:
                        record.is_readonly = True
            else:
                record.is_readonly = False

    @api.constrains('group_id', 'date')
    def _constrains_date(self):
        for record in self:
            if record.date < record.group_id.semester_id.start_time:
                start_time = datetime.strftime(record.group_id.semester_id.start_time, DATE_FORMAT_FR)
                raise ValidationError(f"L'emploi du temps ne peut avoir une date inférieure à la date de début du semestre ({start_time})")

    not_active_slotitems = fields.Integer(
        string='Créneau horaire inactif',
        default=0,
    )

    status = fields.Selection([
        ('pending', 'En attente'),
        ('progress', 'En cours'),
        ('present', 'Présent'),
        ('absent', 'Absent'),
        ('permission', 'Permission'),
        ('exception', 'Exception'),
        ('delay', 'Retard'),
    ], 'Statut',
        default='pending',
    )

    state = fields.Selection([
        ('pending', 'En attente'),
        ('progress', 'En cours'),
        ('present', 'Présent'),
        ('absent', 'Absent'),
        ('permission', 'Permission'),
        ('exception', 'Exception'),
        ('delay', 'Retard'),
    ], string='Statut',
        related='status',
        store=True,
        tracking=True
    )

    class_group_id = fields.Many2one(
        'siantou.ems.core.class.group',
        'Groupe de classe',
        ondelete='cascade'
    )

    subject_day_hour_ids = fields.One2many(
        'siantou.ems.timetable.subject.day.hour',
        'timetable_id',
        string='Jours et heures du cours'
    )

    session_ids = fields.One2many(
        'siantou.ems.core.subject.session',
        'timetable_id',
        'Séances de cours'
    )

    reason = fields.Char(
        string='Motif',
    )

    skip_validation = fields.Boolean('Ignorer la validation ?', default=False)

    is_active = fields.Boolean(string='Actif ?', compute='_compute_active', store=True)

    is_timetable_active = fields.Boolean(string='Emploi du temps actif ?', default=True)

    @api.depends('class_id', 'is_timetable_active', 'status', 'date')
    def _compute_active(self):
        for record in self:
            if record.class_id.is_timetable_active and record.is_timetable_active:
                record.is_active = True
            else:
                if record.is_timetable_active:
                    if record.date and record.class_id.timetable_inactive_date:
                        if record.date < record.class_id.timetable_inactive_date:
                            record.is_active = True
                        else:
                            record.is_active = False
                    else:
                        record.is_active = False
                else:
                    record.is_active = False

    @api.onchange('class_id', 'is_timetable_active', 'status', 'date')
    def _onchange_active(self):
        for record in self:
            if record.class_id.is_timetable_active and record.is_timetable_active:
                record.is_active = True
            else:
                if record.is_timetable_active:
                    if record.date and record.class_id.timetable_inactive_date:
                        if record.date < record.class_id.timetable_inactive_date:
                            record.is_active = True
                        else:
                            record.is_active = False
                    else:
                        record.is_active = False
                else:
                    record.is_active = False

    specialty_id_domain = fields.Binary(compute='_compute_school_domain', default=[])

    subject_id_domain = fields.Binary(compute='_compute_class_domain', default=[])

    school_id_domain = fields.Binary(compute='_compute_group_domain', default=[])

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
    def convert_time_to_float(tm):
        tm = str(tm)
        tm = tm.split(':')
        tm = tm[0:2]
        tm = '.'.join(tm)
        tm = eval(tm)
        tm = float(tm)
        tm = round(tm, 2)
        return tm

    @api.depends('class_id', 'class_group_id', 'subject_id')
    def _compute_name(self):
        for record in self:
            class_name = record.class_id.name if record.class_id.id else ''
            subject_name = record.subject_id.name if record.subject_id.id else ''
            class_group_name = record.class_group_id.name if record.class_group_id.id else ''
            name = '{} - {} - {}'.format(class_name, subject_name, class_group_name)
            while True:
                if name.startswith(' - '):
                    name = re.sub('^ - ', ' ', name)
                elif name.endswith(' - '):
                    name = re.sub(' - $', ' ', name)
                elif name.find(' -  - ') != -1:
                    name = name.replace(' -  - ', ' - ')
                elif name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

    @api.onchange('class_id', 'class_group_id', 'subject_id')
    def _onchange_name(self):
        for record in self:
            class_name = record.class_id.name if record.class_id.id else ''
            subject_name = record.subject_id.name if record.subject_id.id else ''
            class_group_name = record.class_group_id.name if record.class_group_id.id else ''
            name = '{} - {} - {}'.format(class_name, subject_name, class_group_name)
            while True:
                if name.startswith(' - '):
                    name = re.sub('^ - ', ' ', name)
                elif name.endswith(' - '):
                    name = re.sub(' - $', ' ', name)
                elif name.find(' -  - ') != -1:
                    name = name.replace(' -  - ', ' - ')
                elif name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

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
            record.class_group_id = None
            record.specialty_id = None
            record.option_id = None
            record.ue_id = None
            record.subject_id = None

    @api.onchange('school_id')
    def _onchange_school(self):
        for record in self:
            record.field_of_study_id = None
            record.level_id = None
            record.class_id = None
            record.class_group_id = None
            record.specialty_id = None
            record.option_id = None
            record.ue_id = None
            record.subject_id = None

    @api.onchange('level_id')
    def _onchange_level(self):
        for record in self:
            record.class_id = None
            record.class_group_id = None
            record.ue_id = None
            record.subject_id = None

    @api.onchange('specialty_id')
    def _onchange_specialty(self):
        for record in self:
            record.class_id = None
            record.class_group_id = None
            record.option_id = None
            record.ue_id = None
            record.subject_id = None

    @api.onchange('option_id')
    def _onchange_option(self):
        for record in self:
            record.class_id = None
            record.class_group_id = None
            record.ue_id = None
            record.subject_id = None

    @api.onchange('type_cour')
    def _onchange_type_cour(self):
        for record in self:
            record.class_id = None
            record.class_group_id = None
            record.ue_id = None
            record.subject_id = None

    @api.depends('class_id', 'semester_id')
    def _compute_class_domain(self):
        for record in self:
            domain = []
            if record.class_id.id:
                ue_ids = record.class_id.ue_ids.filtered(lambda rec: record.semester_id.id in rec.semester_ids.ids)
                domain = [
                    ('ue_ids', 'in', ue_ids.ids)
                ]
            record.subject_id_domain = domain

    @api.onchange('class_id')
    def _onchange_class(self):
        for record in self:
            record.class_group_id = None
            record.ue_id = None
            record.subject_id = None

    @api.depends('date')
    def _compute_day_of_week(self):
        for record in self:
            if record.date:
                record.day_of_week = str(record.date.weekday())
            else:
                record.day_of_week = None

    @api.onchange('date')
    def _onchange_day_of_week(self):
        for record in self:
            if record.date:
                record.day_of_week = str(record.date.weekday())
            else:
                record.day_of_week = None

    @api.constrains('start_time', 'end_time')
    def _constrains_time(self):
        for record in self:
            if record.start_time < 0.0 or record.end_time < 0.0 or record.start_time > 23.59 or record.end_time > 23.59:
                raise ValidationError("Vous devez définir des heures de début et de fin corrects")
            elif record.start_time >= record.end_time:
                raise ValidationError("L'heure de fin du cours doit être supérieure à l'heure de début du cours")

    @api.constrains('status', 'worked_start_time', 'worked_end_time')
    def _constrains_worked_time(self):
        for record in self:
            if record.worked_start_time < 0.0 or record.worked_end_time < 0.0 or record.worked_start_time > 23.59 or record.worked_end_time > 23.59:
                raise ValidationError("Vous devez définir des heures de début effectuée et de fin effectuée corrects")
            elif record.status in ['present', 'permission'] and record.worked_start_time > record.worked_end_time:
                raise ValidationError("L'heure de fin effectuée du cours doit être supérieure à l'heure de début effectuée du cours")

    @api.constrains('group_id', 'class_id', 'class_group_id', 'employee_id', 'date', 'start_time', 'end_time')
    def _constrains_class(self):
        for record in self:
            if record.skip_validation:
                return True
            group_ids = []
            if record.group_id.group_parent_id.id:
                group_ids.append(record.group_id.group_parent_id.id)
                for group_child_id in record.group_id.group_parent_id.group_child_ids:
                    group_ids.append(group_child_id.id)
            else:
                group_ids.append(record.group_id.id)
                for group_child_id in record.group_id.group_child_ids:
                    group_ids.append(group_child_id.id)

            if record.class_group_id.id:
                timetables = self.env['siantou.ems.timetable.timetable'].search([
                    ('id', '!=', record.id),
                    # ('group_id', 'in', group_ids),
                    ('year_id', '=', record.group_id.semester_id.year_id.id),
                    ('class_id', '=', record.class_id.id),
                    ('class_group_id', '=', record.class_group_id.id),
                    ('date', '=', record.date),
                ]).filtered(lambda rec: not (rec.start_time >= record.end_time or rec.end_time <= record.start_time))
            else:
                timetables = self.env['siantou.ems.timetable.timetable'].search([
                    ('id', '!=', record.id),
                    # ('group_id', 'in', group_ids),
                    ('year_id', '=', record.group_id.semester_id.year_id.id),
                    ('class_id', '=', record.class_id.id),
                    ('class_group_id', '=', False),
                    ('date', '=', record.date),
                ]).filtered(lambda rec: not (rec.start_time >= record.end_time or rec.end_time <= record.start_time))
            timetables = list(timetables)
            if len(timetables) > 0:
                validation_error_message = """
                    Deux cours ne doivent pas être programmés dans la même classe sur des horaires qui se chevauchent le même jour
                    -----
                """
                for timetable in timetables:
                    timetable_date = datetime.strftime(timetable.date, DATE_FORMAT_FR)
                    validation_error_message += f"""
                        • ID: {timetable.id}
                        Version: {timetable.group_id.name}
                        Classe: {timetable.class_id.name}
                        Groupe: {timetable.class_group_id.name}
                        Enseignant: {timetable.employee_id.name}
                        Date: {timetable_date}
                        Heure de début: {timetable.start_time}
                        Heure de fin: {timetable.end_time}
                        -----
                    """
                raise ValidationError(validation_error_message)

            timetables = self.env['siantou.ems.timetable.timetable'].search([
                ('id', '!=', record.id),
                # ('group_id', 'in', group_ids),
                ('year_id', '=', record.group_id.semester_id.year_id.id),
                ('employee_id', '=', record.employee_id.id),
                ('date', '=', record.date),
            ]).filtered(lambda rec: not (rec.start_time >= record.end_time or rec.end_time <= record.start_time or (rec.class_id.level_id.id == record.class_id.level_id.id and rec.start_time == record.start_time and rec.end_time == record.end_time)))
            timetables = list(timetables)
            if len(timetables) > 0:
                validation_error_message = """
                    Deux cours ne doivent pas être programmés pour le même enseignant sur des horaires qui se chevauchent le même jour
                    -----
                """
                for timetable in timetables:
                    timetable_date = datetime.strftime(timetable.date, DATE_FORMAT_FR)
                    validation_error_message += f"""
                        • ID: {timetable.id}
                        Version: {timetable.group_id.name}
                        Classe: {timetable.class_id.name}
                        Groupe: {timetable.class_group_id.name}
                        Enseignant: {timetable.employee_id.name}
                        Date: {timetable_date}
                        Heure de début: {timetable.start_time}
                        Heure de fin: {timetable.end_time}
                        -----
                    """
                raise ValidationError(validation_error_message)

    def create_timetable(self, timetable):
        try:
            timetables = []
            times = [timetable.semester_id.start_time, timetable.semester_id.end_time]
            subject_day_hour_ids = list(timetable.subject_day_hour_ids)
            n = len(subject_day_hour_ids)
            for i, subject_day_hour_id in enumerate(subject_day_hour_ids):
                if i == 0:
                    timetable.write({
                        'date': subject_day_hour_id.start_date,
                        'start_time': subject_day_hour_id.start_time,
                        'end_time': subject_day_hour_id.end_time,
                    })
                    timetables.append(timetable)
                    times = [subject_day_hour_id.start_date, subject_day_hour_id.end_date]
                else:
                    timetable_id = self.env['siantou.ems.timetable.timetable'].create({
                        'department_id': timetable.specialty_id.department_id.id,
                        'school_id': timetable.school_id.id,
                        'level_id': timetable.level_id.id,
                        'specialty_id': timetable.specialty_id.id,
                        'option_id': timetable.option_id.id,
                        'class_id': timetable.class_id.id,
                        'class_group_id': timetable.class_group_id.id,
                        'ue_id': timetable.ue_id.id,
                        'subject_id': timetable.subject_id.id,
                        'is_custom_hours_credit': timetable.is_custom_hours_credit,
                        'hours_credit': timetable.hours_credit,
                        'building_id': timetable.building_id.id,
                        'classroom_id': timetable.classroom_id.id,
                        'employee_id': timetable.employee_id.id,
                        'date': subject_day_hour_id.start_date,
                        'start_time': subject_day_hour_id.start_time,
                        'end_time': subject_day_hour_id.end_time,
                        'group_id': timetable.group_id.id,
                    })
                    timetables.append(timetable_id)
                subject_day_hour_id.unlink()
            if len(timetables) > 0:
                hours_credit = timetable.hours_credit
                hours_credit = math.ceil(hours_credit / n)
                if times[0] == timetable.semester_id.start_time and times[1] == timetable.semester_id.end_time:
                    number_of_week = timetable.semester_id.number_of_week
                else:
                    start_time = times[0]
                    end_time = times[1]
                    diff_days = (end_time - start_time).days
                    number_of_week = math.ceil(diff_days / 7)
                for week in range(0, number_of_week):
                    if hours_credit <= 0:
                        break
                    for first_timetable in timetables:
                        end_time = Timetable.convert_float_to_time(first_timetable.end_time, has_second=True)
                        start_time = Timetable.convert_float_to_time(first_timetable.start_time, has_second=True)
                        end_time = datetime.strptime(f"{first_timetable.date} {end_time}", DATETIME_FORMAT)
                        start_time = datetime.strptime(f"{first_timetable.date} {start_time}", DATETIME_FORMAT)

                        worked_hours = end_time - start_time
                        worked_hours = worked_hours.total_seconds() / 3600.0
                        worked_hours = round(worked_hours, 2)

                        weekly_hours = weekly_hours - first_timetable.not_active_slotitems
                        if worked_hours < 0.0:
                            continue
                        hours_credit -= weekly_hours
                        if hours_credit < 0:
                            break
                        if week > 0:
                            target_date = first_timetable.date + timedelta(weeks=week)
                            timetable_id = self.env['siantou.ems.timetable.timetable'].create({
                                'department_id': first_timetable.specialty_id.department_id.id,
                                'school_id': first_timetable.school_id.id,
                                'level_id': first_timetable.level_id.id,
                                'specialty_id': first_timetable.specialty_id.id,
                                'option_id': first_timetable.option_id.id,
                                'class_id': first_timetable.class_id.id,
                                'class_group_id': first_timetable.class_group_id.id,
                                'ue_id': first_timetable.ue_id.id,
                                'subject_id': first_timetable.subject_id.id,
                                'is_custom_hours_credit': first_timetable.is_custom_hours_credit,
                                'hours_credit': first_timetable.hours_credit,
                                'building_id': first_timetable.building_id.id,
                                'classroom_id': first_timetable.classroom_id.id,
                                'employee_id': first_timetable.employee_id.id,
                                'date': target_date,
                                'start_time': first_timetable.start_time,
                                'end_time': first_timetable.end_time,
                                'group_id': first_timetable.group_id.id,
                            })
            # self.env.cr.commit()
        except psycopg2.errors.NotNullViolation as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except psycopg2.Error as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except Exception as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('base.user_root') and not self.env.user.has_group('base.user_admin') and self.env.user.id != 2:
            if 'status' in vals and vals['status'] in ['present', 'permission']:
                if not self.env.user.has_group('siantou_ems_core.group_timetable_present_perm_create_present'):
                    raise ValidationError(_("Vous n'êtes pas autorisé à créer les enregistrements pour (status in [present, permission]) d'emploi du temps (siantou.ems.timetable.timetable)'."))

        if 'class_id' in vals and 'subject_id' in vals and 'hours_credit' in vals:
            classe = self.env['siantou.ems.core.class'].search([('id', '=', vals['class_id'])], limit=1)
            subject = self.env['siantou.ems.core.subject'].search([('id', '=', vals['subject_id'])], limit=1)
            class_group = None
            if 'class_group_id' in vals:
                class_group = self.env['siantou.ems.core.class.group'].search([('id', '=', vals['class_group_id'])], limit=1)
            if class_group:
                timetables = self.env['siantou.ems.timetable.timetable'].search([
                    '|',
                    '&',
                    '&',
                    ('group_id.is_active', '=', True),
                    ('group_id.is_submit', '=', False),
                    ('group_id.status', '=', 'valid'),
                    '&',
                    '&',
                    '&',
                    ('group_parent_id.is_active', '=', True),
                    ('group_parent_id.is_submit', '=', False),
                    ('group_parent_id.status', '=', 'valid'),
                    ('group_id.status', '=', 'valid'),
                    ('is_active', '=', True),
                    # ('status', 'in', ['present', 'permission']),
                ], order='date asc').filtered(lambda rec: rec.class_id.id == classe.id and rec.class_group_id.id == class_group.id and rec.subject_id.id == subject.id)
            else:
                timetables = self.env['siantou.ems.timetable.timetable'].search([
                    '|',
                    '&',
                    '&',
                    ('group_id.is_active', '=', True),
                    ('group_id.is_submit', '=', False),
                    ('group_id.status', '=', 'valid'),
                    '&',
                    '&',
                    '&',
                    ('group_parent_id.is_active', '=', True),
                    ('group_parent_id.is_submit', '=', False),
                    ('group_parent_id.status', '=', 'valid'),
                    ('group_id.status', '=', 'valid'),
                    ('is_active', '=', True),
                    # ('status', 'in', ['present', 'permission']),
                ], order='date asc').filtered(lambda rec: rec.class_id.id == classe.id and not rec.class_group_id.id and rec.subject_id.id == subject.id)

            timetables = list(timetables)

            total_worked_hours = 0.0
            key_timetables = {}
            for timetable in timetables:
                if not timetable.date or not timetable.day_of_week or not timetable.employee_id.id:
                    continue

                end_time = Timetable.convert_float_to_time(timetable.end_time, has_second=True)
                start_time = Timetable.convert_float_to_time(timetable.start_time, has_second=True)
                key = '{}-{}-{}-{}'.format(timetable.class_id.id, timetable.date, start_time, end_time)
                if key not in key_timetables:
                    key_timetables[key] = {}
                    key_timetables[key]['timetable'] = timetable
                else:
                    continue

                end_time = datetime.strptime(f"{timetable.date} {end_time}", DATETIME_FORMAT)
                start_time = datetime.strptime(f"{timetable.date} {start_time}", DATETIME_FORMAT)

                worked_hours = end_time - start_time
                worked_hours = worked_hours.total_seconds() / 3600.0
                worked_hours = round(worked_hours, 2)

                if worked_hours < 0.0:
                    del(key_timetables[key])
                    continue

                key_timetables[key]['worked_hours'] = worked_hours
                total_worked_hours += key_timetables[key]['worked_hours']

            end_time = Timetable.convert_float_to_time(vals['end_time'], has_second=True)
            start_time = Timetable.convert_float_to_time(vals['start_time'], has_second=True)
            end_time = datetime.strptime(f"{vals['date']} {end_time}", DATETIME_FORMAT)
            start_time = datetime.strptime(f"{vals['date']} {start_time}", DATETIME_FORMAT)

            worked_hours = end_time - start_time
            worked_hours = worked_hours.total_seconds() / 3600.0
            worked_hours = round(worked_hours, 2)

            if worked_hours >= 0.0:
                total_worked_hours += worked_hours
            total_worked_hours = round(total_worked_hours, 2)

            hours_credit = round(subject.hours_credit, 2)

            if total_worked_hours > hours_credit:
                raise ValidationError(f"La somme des volumes horaires programmés doit être inférieure ou égale au volume horaire semestriel {total_worked_hours} / {hours_credit}")

        timetable = super(Timetable, self).create(vals)

        self.create_timetable(timetable)

        return timetable

    def write(self, vals):
        if 'skip_validation' not in vals:
            vals['skip_validation'] = False

        timetable = self.env['siantou.ems.timetable.timetable'].search([('id', '=', self.id)], limit=1)

        if not self.env.user.has_group('base.user_root') and not self.env.user.has_group('base.user_admin') and self.env.user.id != 2:
            if timetable.status in ['present', 'permission']:
                if not self.env.user.has_group('siantou_ems_core.group_timetable_present_perm_write'):
                    raise ValidationError(_("Vous n'êtes pas autorisé à modifier les enregistrements (status in [present, permission]) d'emploi du temps (siantou.ems.timetable.timetable)'."))
            elif timetable.status == 'exception':
                if 'status' in vals and vals['status'] in ['present', 'permission']:
                    if not self.env.user.has_group('siantou_ems_core.group_timetable_exception_perm_write'):
                        raise ValidationError(_("Vous n'êtes pas autorisé à modifier les enregistrements (status = exception) d'emploi du temps (siantou.ems.timetable.timetable)'."))
                    if not self.env.user.has_group('siantou_ems_core.group_timetable_present_perm_write_present'):
                        raise ValidationError(_("Vous n'êtes pas autorisé à modifier les enregistrements pour (status in [present, permission]) d'emploi du temps (siantou.ems.timetable.timetable)'."))
                else:
                    if not self.env.user.has_group('siantou_ems_core.group_timetable_exception_perm_write'):
                        raise ValidationError(_("Vous n'êtes pas autorisé à modifier les enregistrements (status = exception) d'emploi du temps (siantou.ems.timetable.timetable)'."))
            else:
                if 'status' in vals and vals['status'] in ['present', 'permission']:
                    if not self.env.user.has_group('siantou_ems_core.group_timetable_perm_write'):
                        raise ValidationError(_("Vous n'êtes pas autorisé à modifier les enregistrements d'emploi du temps (siantou.ems.timetable.timetable)'."))
                    if not self.env.user.has_group('siantou_ems_core.group_timetable_present_perm_write_present'):
                        raise ValidationError(_("Vous n'êtes pas autorisé à modifier les enregistrements pour (status in [present, permission]) d'emploi du temps (siantou.ems.timetable.timetable)'."))
                else:
                    if not self.env.user.has_group('siantou_ems_core.group_timetable_perm_write'):
                        raise ValidationError(_("Vous n'êtes pas autorisé à modifier les enregistrements d'emploi du temps (siantou.ems.timetable.timetable)'."))

        res = super(Timetable, self).write(vals)

        return res

    def copy(self, default=None):
        timetable = self.env['siantou.ems.timetable.timetable'].search([('id', '=', self.id)], limit=1)

        if not self.env.user.has_group('base.user_root') and not self.env.user.has_group('base.user_admin') and self.env.user.id != 2:
            if timetable.status in ['present', 'permission']:
                if not self.env.user.has_group('siantou_ems_core.group_timetable_present_perm_copy'):
                    raise ValidationError(_("Vous n'êtes pas autorisé à dupliquer les enregistrements (status in [present, permission]) d'emploi du temps (siantou.ems.timetable.timetable)'."))
            elif timetable.status == 'exception':
                if not self.env.user.has_group('siantou_ems_core.group_timetable_exception_perm_copy'):
                    raise ValidationError(_("Vous n'êtes pas autorisé à dupliquer les enregistrements (status = exception) d'emploi du temps (siantou.ems.timetable.timetable)'."))
            else:
                if not self.env.user.has_group('siantou_ems_core.group_timetable_perm_copy'):
                    raise ValidationError(_("Vous n'êtes pas autorisé à dupliquer les enregistrements d'emploi du temps (siantou.ems.timetable.timetable)'."))

        default = dict(default or {})

        res = super(Timetable, self).copy(default=default)

        return res

    def unlink(self):
        timetable = self.env['siantou.ems.timetable.timetable'].search([('id', '=', self.id)], limit=1)

        if not self.env.user.has_group('base.user_root') and not self.env.user.has_group('base.user_admin') and self.env.user.id != 2:
            if timetable.status in ['present', 'permission']:
                if not self.env.user.has_group('siantou_ems_core.group_timetable_present_perm_unlink'):
                    raise ValidationError(_("Vous n'êtes pas autorisé à supprimer les enregistrements (status in [present, permission]) d'emploi du temps (siantou.ems.timetable.timetable)'."))
            elif timetable.status == 'exception':
                if not self.env.user.has_group('siantou_ems_core.group_timetable_exception_perm_unlink'):
                    raise ValidationError(_("Vous n'êtes pas autorisé à supprimer les enregistrements (status = exception) d'emploi du temps (siantou.ems.timetable.timetable)'."))
            else:
                if not self.env.user.has_group('siantou_ems_core.group_timetable_perm_unlink'):
                    raise ValidationError(_("Vous n'êtes pas autorisé à supprimer les enregistrements d'emploi du temps (siantou.ems.timetable.timetable)'."))

        res = super(Timetable, self).unlink()

        return res

    def action_timetable_automatic(self):
        action = self.env.ref('siantou_ems_core.action_generatetimetable_wizard').read()[0]
        action.update({
            'name': 'Planification automatique',
            'res_model': 'siantou.ems.timetable.timetable_wizard',
            'type': 'ir.actions.act_window',
        })
        return action

    def action_open_filter(self):
        view_id = self.env.ref('siantou_ems_core.timetable_filter_wizard').id
        return {
            'name': 'Filtre des emplois du temps',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'timetable.filter.wizard',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': {
                'default_year_id': self.env['siantou.ems.core.year'].search([('is_active', '=', True)], limit=1).id,
                'default_status': None,
            },
        }

    def action_reset_filter(self):
        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', '')
        action = self.env.ref('siantou_ems_core.action_show_timetable').read()[0]
        action.update({
            'target': 'main',
        })
        return action

    def action_print_pdf(self):
        active_ids = self.env.context.get('active_ids', [])
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')
        report_data = self.env['timetable.print.wizard'].create({})
        domains = [
            ('id', 'in', active_ids)
        ]
        data = report_data.print_timetable_report_data(domains=domains)

        if len(data['docdata']['timetable_data'].keys()) == 0:
            raise UserError('Aucune donnée trouvée')
        report_action = self.env.ref('siantou_ems_core.action_report_timetable')
        report_action.update({
            'name': 'Emplois du temps PDF',
        })
        return report_action.report_action(self, data=data)

    def action_present_timetable(self):
        active_ids = self.env.context.get('active_ids', [])
        timetable_ids = self.env['siantou.ems.timetable.timetable'].browse(active_ids)
        timetable_ids = list(timetable_ids)
        for timetable in timetable_ids:
            timetable.write({
                'worked_start_time': timetable.start_time,
                'worked_end_time': timetable.end_time,
                'worked_time': 0.0,
                'rate': 0.0,
                'amount': 0.0,
                'status': 'present',
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_absent_timetable(self):
        active_ids = self.env.context.get('active_ids', [])
        timetable_ids = self.env['siantou.ems.timetable.timetable'].browse(active_ids)
        timetable_ids = list(timetable_ids)
        for timetable in timetable_ids:
            timetable.write({
                'status': 'absent',
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_delay_timetable(self):
        active_ids = self.env.context.get('active_ids', [])
        timetable_ids = self.env['siantou.ems.timetable.timetable'].browse(active_ids)
        timetable_ids = list(timetable_ids)
        for timetable in timetable_ids:
            timetable.write({
                'status': 'delay',
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def state_pending_timetable(self):
        self.write({
            'worked_start_time': 0.0,
            'worked_end_time': 0.0,
            'worked_time': 0.0,
            'rate': 0.0,
            'amount': 0.0,
            'status': 'pending',
            'reason': None,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def state_progress_timetable(self):
        self.write({
            'worked_start_time': 0.0,
            'worked_end_time': 0.0,
            'worked_time': 0.0,
            'rate': 0.0,
            'amount': 0.0,
            'status': 'progress',
            'reason': None,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def state_present_timetable(self):
        self.write({
            'worked_start_time': self.start_time,
            'worked_end_time': self.end_time,
            'worked_time': 0.0,
            'rate': 0.0,
            'amount': 0.0,
            'status': 'present',
            'reason': None,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def state_absent_timetable(self):
        self.write({
            'worked_start_time': 0.0,
            'worked_end_time': 0.0,
            'worked_time': 0.0,
            'rate': 0.0,
            'amount': 0.0,
            'status': 'absent',
            'reason': None,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def state_permission_timetable(self):
        self.write({
            'worked_start_time': 0.0,
            'worked_end_time': 0.0,
            'worked_time': 0.0,
            'rate': 0.0,
            'amount': 0.0,
            'status': 'permission',
            'reason': None,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def state_exception_timetable(self):
        self.write({
            'worked_start_time': 0.0,
            'worked_end_time': 0.0,
            'worked_time': 0.0,
            'rate': 0.0,
            'amount': 0.0,
            'status': 'exception',
            'reason': None,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def state_delay_timetable(self):
        self.write({
            'worked_start_time': 0.0,
            'worked_end_time': 0.0,
            'worked_time': 0.0,
            'rate': 0.0,
            'amount': 0.0,
            'status': 'delay',
            'reason': None,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def update_timetable(self, timetable):
        try:
            timetable.write({
                'worked_start_time': timetable.start_time,
                'worked_end_time': timetable.end_time,
            })
            # self.env.cr.commit()
        except psycopg2.errors.NotNullViolation as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except psycopg2.Error as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except Exception as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

    def action_update_all_timetable(self):
        active_ids = self.env.context.get('active_ids', [])
        timetables = self.env['siantou.ems.timetable.timetable'].browse(active_ids)
        timetables = list(timetables)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')

        for timetable in timetables:
            self.update_timetable(timetable)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

class TimetableGroup(models.Model):
    _name = 'siantou.ems.timetable.group'
    _description = 'Version d\'emploi du temps'

    group_name = fields.Char(
        string='Nom',
        required=True
    )

    name = fields.Char(
        string='Nom de la version',
        compute='_compute_name', store=True,
    )

    timetable_ids = fields.One2many(
        'siantou.ems.timetable.timetable',
        'group_id',
        string='Emplois du temps'
    )

    semester_id = fields.Many2one(
        'siantou.ems.core.year.semester',
        string='Semestre',
        required=True
    )

    year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année académique',
        related='semester_id.year_id',
        store=True
    )

    is_active = fields.Boolean(string='Actif ?', default=False)

    is_submit = fields.Boolean(string='Soumis ?', default=True)

    read_user_ids = fields.Many2many(
        'res.users',
        'read_user_group_rel',
        'group_id',
        'user_id',
        string='Utilisateurs associés en lecture',
    )

    write_user_ids = fields.Many2many(
        'res.users',
        'write_user_group_rel',
        'group_id',
        'user_id',
        string='Utilisateurs associés en écriture',
    )

    group_parent_id = fields.Many2one(
        'siantou.ems.timetable.group',
        string='Version d\'emploi du temps parent',
        domain="[('is_submit', '=', False), ('semester_id', '=', semester_id), ('status', '=', 'valid')]",
        ondelete='cascade'
    )

    group_child_ids = fields.One2many(
        'siantou.ems.timetable.group',
        'group_parent_id',
        string='Versions d\'emploi du temps enfants',
        domain="[('is_submit', '=', True), ('semester_id', '=', semester_id), ('status', '=', 'valid')]",
    )

    school_ids = fields.Many2many('siantou.ems.core.school', 'school_group_rel', 'group_id', 'school_id', string='Écoles')

    status = fields.Selection([
        ('pending', 'En attente'),
        ('valid', 'Valide'),
        ('invalid', 'Invalide'),
        ('draft', 'Brouillon'),
    ], 'Statut',
        default='pending',
    )

    state = fields.Selection([
        ('pending', 'En attente'),
        ('valid', 'Valide'),
        ('invalid', 'Invalide'),
        ('draft', 'Brouillon'),
    ], string='Statut',
        related='status',
        store=True,
        tracking=True
    )

    description = fields.Text(
        string='Description de la version',
    )

    department_ids = fields.Many2many('hr.department', 'department_group_rel', 'group_id', 'department_id', string='Départements')

    department_id_domain = fields.Binary(compute='_compute_school_domain', default=[])

    class_id_domain = fields.Binary(compute='_compute_department_domain', default=[])

    @api.depends('school_ids')
    def _compute_school_domain(self):
        for record in self:
            school_ids = record.school_ids
            domain = [
                ('school_id', 'in', school_ids.ids),
            ]
            record.department_id_domain = domain

    @api.depends('school_ids', 'department_ids', 'semester_id')
    def _compute_department_domain(self):
        for record in self:
            school_ids = record.school_ids
            department_ids = record.department_ids
            domain = [
                ('school_id', 'in', school_ids.ids),
            ]
            if len(department_ids.ids) > 0:
                domain.append(('specialty_id.department_id', 'in', department_ids.ids))
            if record.semester_id.id:
                domain.append(('year_id', '=', record.semester_id.year_id.id))
            record.class_id_domain = domain

    class_ids = fields.Many2many('siantou.ems.core.class', 'class_group_rel', 'group_id', 'class_id', string='Classes')

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

    @api.constrains('start_date', 'end_date')
    def _constrains_date(self):
        for record in self:
            if record.start_date > record.end_date:
                raise ValidationError('La date de fin doit être supérieure ou égale à la date de début')

    has_write_access = fields.Boolean(string='Accès en écriture ?', compute='_compute_access', store=True)

    @api.depends('start_date', 'end_date')
    def _compute_access(self):
        for record in self:
            current_date = date.today()
            if record.start_date and record.end_date:
                if record.start_date > current_date or record.end_date <= current_date:
                    record.has_write_access = False
                else:
                    record.has_write_access = True
            else:
                record.has_write_access = False

    @api.onchange('start_date', 'end_date')
    def _onchange_access(self):
        for record in self:
            current_date = date.today()
            if record.start_date and record.end_date:
                if record.start_date > current_date or record.end_date <= current_date:
                    record.has_write_access = False
                else:
                    record.has_write_access = True
            else:
                record.has_write_access = False

    is_readonly = fields.Boolean(string='Lecture unique ?', compute='_compute_readonly', store=False)

    @api.depends('start_date', 'end_date', 'write_user_ids')
    def _compute_readonly(self):
        for record in self:
            current_date = date.today()
            if record.create_uid.id:
                if record.create_uid.id == self.env.user.id:
                    record.is_readonly = False
                else:
                    if self.env.user.id in record.write_user_ids.ids:
                        if record.start_date > current_date or record.end_date <= current_date:
                            record.is_readonly = True
                        else:
                            record.is_readonly = False
                    else:
                        record.is_readonly = True
            else:
                record.is_readonly = False

    @api.onchange('start_date', 'end_date', 'write_user_ids')
    def _onchange_readonly(self):
        for record in self:
            current_date = date.today()
            if record.create_uid.id:
                if record.create_uid.id == self.env.user.id:
                    record.is_readonly = False
                else:
                    if self.env.user.id in record.write_user_ids.ids:
                        if record.start_date > current_date or record.end_date <= current_date:
                            record.is_readonly = True
                        else:
                            record.is_readonly = False
                    else:
                        record.is_readonly = True
            else:
                record.is_readonly = False

    @api.depends('group_name', 'is_submit', 'is_active')
    def _compute_name(self):
        for record in self:
            name = record.group_name if record.group_name else ''
            name = name.lower()
            while True:
                if name.find('(soumis)') != -1:
                    name = name.replace('(soumis)', '')
                elif name.find('(actif)') != -1:
                    name = name.replace('(actif)', '')
                else:
                    break
            if record.is_submit:
                name = '{} (soumis)'.format(name)
            elif record.is_active:
                name = '{} (actif)'.format(name)
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

    @api.onchange('group_name', 'is_submit', 'is_active')
    def _onchange_name(self):
        for record in self:
            name = record.group_name if record.group_name else ''
            name = name.lower()
            while True:
                if name.find('(soumis)') != -1:
                    name = name.replace('(soumis)', '')
                elif name.find('(actif)') != -1:
                    name = name.replace('(actif)', '')
                else:
                    break
            if record.is_submit:
                name = '{} (soumis)'.format(name)
            elif record.is_active:
                name = '{} (actif)'.format(name)
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

    @api.constrains('is_submit', 'is_active')
    def _constrains_default(self):
        for record in self:
            if record.is_submit:
                if record.is_active:
                    raise ValidationError(f"Une version d'emploi du temps soumise ne peut être active")
            else:
                if record.is_active:
                    groups = self.env['siantou.ems.timetable.group'].search([
                        ('id', '!=', record.id),
                        ('is_active', '=', True),
                    ])
                    groups = list(groups)
                    if len(groups) > 1:
                        raise ValidationError(f"Deux versions d'emploi du temps sont déjà actives")

    def update_timetable_group(self, group):
        try:
            group_child_ids = group.group_child_ids.ids
            exist_group_child_ids = []
            for timetable_id in group.timetable_ids:
                if timetable_id.group_child_id.id:
                    if timetable_id.group_child_id.id not in group_child_ids:
                        timetable_id.unlink()
                    else:
                        exist_group_child_ids.append(timetable_id.group_child_id.id)
            exist_group_child_ids = list(set(exist_group_child_ids))
            for group_child_id in group.group_child_ids:
                if group_child_id.id not in exist_group_child_ids:
                    for timetable_id in group_child_id.timetable_ids:
                        group.timetable_ids.create({
                            'semester_id': timetable_id.semester_id.id,
                            'school_id': timetable_id.school_id.id,
                            'field_of_study_id': timetable_id.field_of_study_id.id,
                            'level_id': timetable_id.level_id.id,
                            'specialty_id': timetable_id.specialty_id.id,
                            'class_id': timetable_id.class_id.id,
                            'class_group_id': timetable_id.class_group_id.id,
                            'ue_id': timetable_id.ue_id.id,
                            'subject_id': timetable_id.subject_id.id,
                            'is_custom_hours_credit': timetable_id.is_custom_hours_credit,
                            'hours_credit': timetable_id.hours_credit,
                            'building_id': timetable_id.building_id.id,
                            'classroom_id': timetable_id.classroom_id.id,
                            'employee_id': timetable_id.employee_id.id,
                            'date': timetable_id.date,
                            'start_time': timetable_id.start_time,
                            'end_time': timetable_id.end_time,
                            'group_id': group.id,
                            'group_child_id': group_child_id.id,
                            'status': 'pending',
                        })
            # self.env.cr.commit()
        except psycopg2.errors.NotNullViolation as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except psycopg2.Error as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except Exception as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

    @api.model
    def create(self, vals):
        group = super(TimetableGroup, self).create(vals)

        # if not group.is_submit:
        #     self.update_timetable_group(group)

        return group

    def write(self, vals):
        group = self.env['siantou.ems.timetable.group'].search([('id', '=', self.id)], limit=1)

        res = super(TimetableGroup, self).write(vals)

        # if not group.is_submit:
        #     self.update_timetable_group(group)

        return res

    def state_pending_timetable_group(self):
        self.write({
            'status': 'pending',
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def state_valid_timetable_group(self):
        self.write({
            'status': 'valid',
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def state_invalid_timetable_group(self):
        self.write({
            'status': 'invalid',
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def state_draft_timetable_group(self):
        self.write({
            'status': 'draft',
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_open_copy(self):
        view_id = self.env.ref('siantou_ems_core.timetable_group_copy_wizard').id
        return {
            'name': 'Copie des versions d\'emploi du temps',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'timetable.group.copy.wizard',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': {
                'default_source_year_id': self.env['siantou.ems.core.year'].search([('is_active', '=', True)], limit=1).id,
                'default_is_submit': False,
            },
        }

    def action_open_copy_submit(self):
        view_id = self.env.ref('siantou_ems_core.timetable_group_copy_wizard').id
        return {
            'name': 'Copie des versions d\'emploi du temps',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'timetable.group.copy.wizard',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': {
                'default_source_year_id': self.env['siantou.ems.core.year'].search([('is_active', '=', True)], limit=1).id,
            },
        }

    def action_open_move(self):
        view_id = self.env.ref('siantou_ems_core.timetable_group_move_wizard').id
        return {
            'name': 'Déplacement des versions d\'emploi du temps',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'timetable.group.move.wizard',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': {
                'default_year_id': self.env['siantou.ems.core.year'].search([('is_active', '=', True)], limit=1).id,
                'default_is_submit': False,
            },
        }

    def action_open_move_submit(self):
        view_id = self.env.ref('siantou_ems_core.timetable_group_move_wizard').id
        return {
            'name': 'Déplacement des versions d\'emploi du temps',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'timetable.group.move.wizard',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': {
                'default_year_id': self.env['siantou.ems.core.year'].search([('is_active', '=', True)], limit=1).id,
            },
        }

class TimetableSlotItem(models.Model):
    _name = 'siantou.ems.timetable.slotitem'
    _description = 'Plage horaire'

    slot_id = fields.Many2one(
        'siantou.ems.timetable.slot',
        string='Créneau horaire',
        ondelete='cascade',
    )

    # Heure de début du cours
    start_time = fields.Float(
        string='Heure de début',
        required=True,
        default=0.0,
        widget='time'
    )

    # Heure de fin du cours
    end_time = fields.Float(
        string='Heure de fin',
        required=True,
        default=0.0,
        widget='time'
    )

    type = fields.Selection(
        selection=[('0', 'Soir'), ('1', 'Jour')],
        string='Type',
        default='1',
        widget='radio'
    )

    is_active = fields.Boolean(string='Actif ?', default=True)

    @staticmethod
    def are_almost_equal(a, b, tolerance=1e-9):
        return abs(a - b) < tolerance

    @api.constrains('start_time', 'end_time')
    def _constrains_time(self):
        for record in self:
            if record.start_time < 0.0 or record.end_time < 0.0 or record.start_time > 23.59 or record.end_time > 23.59:
                raise ValidationError("Vous devez définir des heures de début et de fin corrects")
            elif record.start_time > record.end_time:
                raise ValidationError("L'heure de fin du cours doit être supérieure à l'heure de début du cours")
            elif not TimetableSlotItem.are_almost_equal(round((record.end_time - record.start_time), 2), round(1.00, 2)):
                raise ValidationError(f"La plage horaire entre l'heure de début et l'heure de fin ne doit pas être supérieure ou inférieure 1")
            else:
                slotitems = self.env['siantou.ems.timetable.slotitem'].search([
                    ('id', '!=', record.id),
                    ('slot_id', '=', record.slot_id.id),
                ]).filtered(lambda rec: not (rec.start_time >= record.end_time or rec.end_time <= record.start_time))
                slotitems = list(slotitems)
                if len(slotitems) > 0:
                    raise ValidationError(f"La plage horaire entre l'heure de début et l'heure de fin n'est pas disponible")

class TimetableSlot(models.Model):
    _name = 'siantou.ems.timetable.slot'
    _description = 'Créneau horaire'

    name = fields.Char(
        string='Nom',
        required=True
    )

    slotitem_day_ids = fields.One2many(
        'siantou.ems.timetable.slotitem',
        'slot_id',
        string='Plages horaires jour',
        domain=[('type', '=', '1')]
    )

    slotitem_night_ids = fields.One2many(
        'siantou.ems.timetable.slotitem',
        'slot_id',
        string='Plages horaires soir',
        domain=[('type', '=', '0')]
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Département'
    )

    specialty_ids = fields.One2many(
        'siantou.ems.core.specialty',
        'slot_id',
        string='Spécialités'
    )

    is_active = fields.Boolean(string='Actif ?', default=False)

    @api.constrains('is_active')
    def _constrains_default(self):
        for record in self:
            if record.is_active:
                slots = self.env['siantou.ems.timetable.slot'].search([
                    ('id', '!=', record.id),
                    ('is_active', '=', True),
                ])
                slots = list(slots)
                if len(slots) > 0:
                    raise ValidationError(f"Créneau horaire actif déjà défini")

    @api.onchange('department_id')
    def _onchange_department(self):
        for record in self:
            if record.department_id.id:
                record.specialty_ids = self.env['siantou.ems.core.specialty'].search([
                    ('department_id', '=', record.department_id.id),
                ])
            else:
                record.specialty_ids = []
