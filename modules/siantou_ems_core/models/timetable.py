# -*- coding: utf-8 -*-

import math
from email.policy import default
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
import psycopg2
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import pytz
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
        'Date de début',
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
        'Date de fin',
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
        'Version',
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

    # Contrainte logique pour s'assurer que la date de fin est supérieure à la date de début
    @api.constrains('start_date', 'end_date')
    def _constrains_date(self):
        for record in self:
            if record.start_date > record.end_date:
                raise ValidationError('La date de fin doit être supérieure ou égale à la date de début')

    # Méthode pour remplir automatiquement le jour de la semaine
    @api.onchange('start_date')
    def _onchange_start_date(self):
        for record in self:
            if record.start_date:
                record.day_of_week = str(record.start_date.weekday())
            else:
                record.day_of_week = None

    @api.depends('start_date')
    def _compute_day_of_week(self):
        for record in self:
            if record.start_date:
                record.day_of_week = str(record.start_date.weekday())
            else:
                record.day_of_week = None

    # Contrainte logique pour s'assurer que les heures de début et de fin sont définies et que l'heure de fin est supérieure à l'heure de début
    @api.constrains('start_time', 'end_time')
    def _constrains_time(self):
        for record in self:
            if record.start_time <= 0.0 or record.end_time <= 0.0:
                raise ValidationError("Vous devez définir des heures de début et de fin corrects")
            elif record.end_time <= record.start_time:
                raise ValidationError("L'heure de fin du cours doit être supérieure à l'heure de début du cours")

class Timetable(models.Model):
    _name = 'siantou.ems.timetable.timetable'
    _description = 'Emplois du temps'

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

    batch_id = fields.Many2one(
        'siantou.ems.core.student.batch',
        string='Lot d\'étudiants'
    )

    # Ajouter un champ de relation vers hr.department pour lier la filière au département
    department_id = fields.Many2one(
        'hr.department',
        string='Département'
    )

    school_id = fields.Many2one(
        'siantou.ems.core.school',
        string='Ecole',
        required=True,
        ondelete='cascade'
    )

    # Niveau lié à la programmation de cours
    level_id = fields.Many2one(
        'siantou.ems.core.level',
        'Niveau',
        required=True,
        ondelete='cascade'
    )

    # Filière liée à la programmation de cours
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
        'Cours',
        required=True,
        ondelete='cascade'
    )

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
        'Date du jour',
        # required=True,
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

    @api.depends('date', 'worked_start_time', 'worked_end_time')
    def _compute_worked_time(self):
        for record in self:
            if record.date and record.worked_start_time and record.worked_end_time:
                end_time = Timetable.convert_float_to_time(record.worked_end_time)
                start_time = Timetable.convert_float_to_time(record.worked_start_time)
                datetime_to = datetime.strptime(f"{record.date} {end_time}", DATETIME_FORMAT)
                datetime_from = datetime.strptime(f"{record.date} {start_time}", DATETIME_FORMAT)
                worked_hours = datetime_to - datetime_from
                worked_hours = worked_hours.total_seconds() / 3600.0
                worked_hours = round(worked_hours, 2)
                record.worked_time = worked_hours
            else:
                record.worked_time = 0.0

    # Heure de fin du cours
    worked_time = fields.Float(
        'Heure effectuée',
        default=0.0,
        # compute='_compute_worked_time',
        # store=True
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

    # Version auquel appartient l'emploi du temps
    group_id = fields.Many2one(
        'siantou.ems.timetable.group',
        'Version',
        required=True,
        # default=_default_group,
        ondelete='cascade'
    )

    group_child_id = fields.Many2one(
        'siantou.ems.timetable.group',
        'Version d\'emploi du temps soumise',
        domain="[('is_submit', '=', True), ('semester_id', '=', semester_id), ('status', '=', 'valid')]",
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

    state = fields.Selection([
        ('pending', 'En attente'),
        ('progress', 'En cours'),
        ('present', 'Présent'),
        ('absent', 'Absent'),
        ('permission', 'Permission'),
        ('exception', 'Exception'),
        ('delay', 'Retard'),
    ], 'Statut',
        related='status',
        store=True,
        tracking=True
    )

    class_group_id = fields.Many2one(
        'siantou.ems.core.class.group',
        'Groupe',
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

    specialty_id_domain = fields.Binary(compute='_compute_school_domain', default=[])

    subject_id_domain = fields.Binary(compute='_compute_class_domain', default=[])

    @staticmethod
    def convert_float_to_time(tm):
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

    @api.depends('class_id', 'subject_id')
    def _compute_name(self):
        for record in self:
            class_name = record.class_id.name if record.class_id.id else ''
            subject_name = record.subject_id.name if record.subject_id.id else ''
            if subject_name != '':
                subject_name = f'- {subject_name}'
            name = '{} {}'.format(class_name, subject_name)
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

    @api.onchange('class_id', 'subject_id')
    def _onchange_name(self):
        for record in self:
            class_name = record.class_id.name if record.class_id.id else ''
            subject_name = record.subject_id.name if record.subject_id.id else ''
            if subject_name != '':
                subject_name = f'- {subject_name}'
            name = '{} {}'.format(class_name, subject_name)
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

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

    @api.depends('class_id')
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

    # Méthode pour remplir automatiquement le jour de la semaine
    @api.onchange('date')
    def _onchange_date(self):
        for record in self:
            if record.date:
                record.day_of_week = str(record.date.weekday())
            else:
                record.day_of_week = None

    @api.depends('date')
    def _compute_day_of_week(self):
        for record in self:
            if record.date:
                record.day_of_week = str(record.date.weekday())
            else:
                record.day_of_week = None

    # Contrainte logique pour se rassurer que deux cours ne sont pas programmés dans la même salle de classe sur des horaires qui se chevauchent le même jour
    # @api.constrains('classroom_id', 'date', 'subject_id', 'level_id', 'start_time', 'end_time')
    # def _constrains_classroom_is_free(self):
    #     for record in self:
    #         timetables = self.search([
    #             ('id', '!=', record.id),
    #             ('classroom_id', '=', record.classroom_id.id),
    #             ('date', '=', record.date),
    #             '|',
    #             ('subject_id', '!=', record.subject_id.id),
    #             ('level_id', '!=', record.level_id.id),
    #         ]).filtered(lambda rec: not (rec.start_time >= record.end_time or rec.end_time <= record.start_time))
    #         timetables = list(timetables)
    #         if len(timetables) > 0:
    #             raise ValidationError("Deux cours ne doivent pas être programmés dans la même salle de classe sur des horaires qui se chevauchent le même jour")

    # Contrainte logique pour s'assurer que les heures de début et de fin sont définies et que l'heure de fin est supérieure à l'heure de début
    # @api.constrains('start_time', 'end_time')
    # def _constrains_time(self):
    #     for record in self:
    #         if record.start_time <= 0.0 or record.end_time <= 0.0:
    #             raise ValidationError("Vous devez définir des heures de début et de fin corrects")
    #         elif record.end_time <= record.start_time:
    #             raise ValidationError("L'heure de fin du cours doit être supérieure à l'heure de début du cours")

    def create_timetable(self, timetable):
        try:
            timetables = []
            times = [timetable.semester_id.start_time, timetable.semester_id.end_time]
            subject_day_hour_ids = list(timetable.subject_day_hour_ids)
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
                        'department_id': timetable.field_of_study_id.department_id.id,
                        'school_id': timetable.school_id.id,
                        'level_id': timetable.level_id.id,
                        'specialty_id': timetable.specialty_id.id,
                        'option_id': timetable.option_id.id,
                        'class_id': timetable.class_id.id,
                        'class_group_id': timetable.class_group_id.id,
                        'ue_id': timetable.ue_id.id,
                        'subject_id': timetable.subject_id.id,
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
                semester_hours_credit = timetable.subject_id.hours_credit
                if times[0] == timetable.semestre_id.start_time and times[1] == timetable.semestre_id.end_time:
                    number_of_week = timetable.semestre_id.number_of_week
                else:
                    start_time = times[0]
                    end_time = times[1]
                    diff_days = (end_time - start_time).days
                    number_of_week = math.ceil(diff_days / 7)
                for week in range(0, number_of_week):
                    if semester_hours_credit <= 0:
                        break
                    for first_timetable in timetables:
                        weekly_hours = first_timetable.end_time - first_timetable.start_time
                        weekly_hours = weekly_hours - first_timetable.not_active_slotitems
                        semester_hours_credit -= weekly_hours
                        if week > 0:
                            target_date = first_timetable.date + timedelta(weeks=week)
                            timetable_id = self.env['siantou.ems.timetable.timetable'].create({
                                'department_id': first_timetable.field_of_study_id.department_id.id,
                                'school_id': first_timetable.school_id.id,
                                'level_id': first_timetable.level_id.id,
                                'specialty_id': first_timetable.specialty_id.id,
                                'option_id': first_timetable.option_id.id,
                                'class_id': first_timetable.class_id.id,
                                'class_group_id': first_timetable.class_group_id.id,
                                'ue_id': first_timetable.ue_id.id,
                                'subject_id': first_timetable.subject_id.id,
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
        timetable = super(Timetable, self).create(vals)

        self.create_timetable(timetable)

        return timetable

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
        timetables = self.env['siantou.ems.timetable.timetable'].browse(active_ids)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')
        report_data = self.env['timetable.print.wizard'].create({
            'group_id': timetables[0].group_id.id,
        })
        domain = [
            ('id', 'in', active_ids)
        ]
        data = report_data.print_timetable_report_data(domain)

        # Appeler le rapport PDF
        if not data['docdata']['timetable_data']:
            raise UserError('Aucune donnée trouvée')
        report_action = self.env.ref('siantou_ems_core.action_report_timetable')
        return report_action.report_action(self, data=data)

    def action_present_timetable(self):
        active_ids = self.env.context.get('active_ids', [])
        timetable_ids = self.env['siantou.ems.timetable.timetable'].browse(active_ids)
        for timetable in timetable_ids:
            timetable.write({
                'status': 'present',
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_absent_timetable(self):
        active_ids = self.env.context.get('active_ids', [])
        timetable_ids = self.env['siantou.ems.timetable.timetable'].browse(active_ids)
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
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def update_timetable(self, timetable):
        try:
            if timetable.worked_start_time == 0.0 and timetable.worked_end_time == 0.0:
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

    is_active = fields.Boolean(string="Actif", default=False)

    is_submit = fields.Boolean(string="Soumis", default=True)

    user_ids = fields.Many2many(
        'res.users',
        'user_group_rel',
        'group_id',
        'user_id',
        string='Utilisateurs associés',
    )

    group_parent_ids = fields.Many2many(
        'siantou.ems.timetable.group',
        'group_parent_child_rel',
        'group_child_id',
        'group_parent_id',
        string='Versions d\'emploi du temps publiées',
        domain="[('is_submit', '=', False), ('semester_id', '=', semester_id)]",
    )

    group_child_ids = fields.Many2many(
        'siantou.ems.timetable.group',
        'group_parent_child_rel',
        'group_parent_id',
        'group_child_id',
        string='Versions d\'emploi du temps soumises',
        domain="[('is_submit', '=', True), ('semester_id', '=', semester_id), ('status', '=', 'valid')]",
    )

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
    ], 'Statut',
        related='status',
        store=True,
        tracking=True
    )

    description = fields.Text(
        string='Description de la version',
    )

    @api.depends('is_submit', 'is_active')
    def _compute_name(self):
        for record in self:
            if record.name:
                name = record.name
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

    @api.onchange('is_submit', 'is_active')
    def _onchange_name(self):
        for record in self:
            if record.name:
                name = record.name
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

    @api.constrains('is_active')
    def _constrains_default(self):
        for record in self:
            if record.is_active:
                slots = self.env['siantou.ems.timetable.group'].search([
                    ('id', '!=', record.id),
                    ('is_active', '=', True),
                ])
                slots = list(slots)
                if len(slots) > 0:
                    raise ValidationError(f"Version active déjà définie")

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

        if not group.is_submit:
            self.update_timetable_group(group)

        return group

    def write(self, vals):
        group = self.env['siantou.ems.timetable.group'].search([('id', '=', self.id)], limit=1)

        res = super(TimetableGroup, self).write(vals)

        if not group.is_submit:
            self.update_timetable_group(group)

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

    def action_open_copier(self):
        view_id = self.env.ref('siantou_ems_core.timetable_group_copier_wizard').id
        return {
            'name': 'Copieur des versions d\'emploi du temps',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'timetable.group.copier.wizard',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': {
                'default_source_year_id': self.env['siantou.ems.core.year'].search([('is_active', '=', True)], limit=1).id,
                'default_is_submit': False,
            },
        }

    def action_open_copier_submit(self):
        view_id = self.env.ref('siantou_ems_core.timetable_group_copier_wizard').id
        return {
            'name': 'Copieur des versions d\'emploi du temps',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'timetable.group.copier.wizard',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': {
                'default_source_year_id': self.env['siantou.ems.core.year'].search([('is_active', '=', True)], limit=1).id,
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

    is_active = fields.Boolean(string="Actif", default=True)

    @staticmethod
    def are_almost_equal(a, b, tolerance=1e-9):
        return abs(a - b) < tolerance

    @api.constrains('start_time', 'end_time')
    def _constrains_time(self):
        for record in self:
            if record.start_time > record.end_time:
                raise ValidationError(f"L'heure de début ne doit pas être supérieure à l'heure de fin")
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

    field_of_study_ids = fields.One2many(
        'siantou.ems.core.field_of_study',
        'slot_id',
        string='Filières'
    )

    is_active = fields.Boolean(string="Actif", default=False)

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
                record.field_of_study_ids = self.env['siantou.ems.core.field_of_study'].search([
                    ('department_id', '=', record.department_id.id),
                ])
            else:
                record.field_of_study_ids = []
