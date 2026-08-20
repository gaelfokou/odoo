# -*- coding: utf-8 -*-

import re
from random import randint
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
import psycopg2
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
from odoo.tools import unique
import logging

_logger = logging.getLogger(__name__)


class OptionOfStudy(models.Model):
    _name = 'siantou.ems.core.option'
    _description = 'Option'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    specialty_id = fields.Many2one(
        'siantou.ems.core.specialty',
        string='Spécialité',
        required=True,
    )

    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        string='Filière',
        related='specialty_id.field_of_study_id'
    )

    cycle_id = fields.Many2one(
        'oe.school.course',
        string='Cursus ou Cycle',
        related='specialty_id.cycle_id'
    )

    supervision_id = fields.Many2one(
        'oe.school.course.supervision',
        string='Tutelle académique',
        related='cycle_id.supervision_id'
    )

    code = fields.Char(
        string='Code',
        required=True
    )

    option_name = fields.Char(
        string='Nom',
        required=True
    )

    name = fields.Char(
        string='Nom de l\'option',
        compute='_compute_name',
        store=True,
    )

    @api.depends('option_name', 'supervision_id')
    def _compute_name(self):
        for record in self:
            option_name = record.option_name if record.option_name else ''
            option_name = option_name.lower()
            while True:
                if option_name.find('-') != -1:
                    option_name = option_name.replace('-', ' ')
                else:
                    break
            supervision_name = record.supervision_id.name if record.supervision_id.id else ''
            if supervision_name != '':
                supervision_name = f'- {supervision_name}'
            supervisions = self.env['oe.school.course.supervision'].search([])
            supervisions = list(supervisions)
            for supervision in supervisions:
                name = supervision.name
                name = name.lower()
                while True:
                    if option_name.find(name) != -1:
                        option_name = option_name.replace(name, '')
                    else:
                        break
                names = name.split('/')
                for name in names:
                    while True:
                        if option_name.find(name) != -1:
                            option_name = option_name.replace(name, '')
                        else:
                            break
            name = '{} {}'.format(option_name, supervision_name)
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

    @api.onchange('option_name', 'supervision_id')
    def _onchange_name(self):
        for record in self:
            record._compute_name()

    _sql_constraints = [
        ('unique_code', 'unique(code)', "Le code de l'option doit être unique."),
    ]

    def update_option(self, option):
        try:
            option_name = option.name if option.name else ''
            option_name = option_name.lower()
            while True:
                if option_name.find('-') != -1:
                    option_name = option_name.replace('-', ' ')
                else:
                    break
            supervisions = self.env['oe.school.course.supervision'].search([])
            supervisions = list(supervisions)
            for supervision in supervisions:
                name = supervision.name
                name = name.lower()
                while True:
                    if option_name.find(name) != -1:
                        option_name = option_name.replace(name, '')
                    else:
                        break
                names = name.split('/')
                for name in names:
                    while True:
                        if option_name.find(name) != -1:
                            option_name = option_name.replace(name, '')
                        else:
                            break
            name = option_name
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            option.write({
                'option_name': name,
            })
        except psycopg2.errors.NotNullViolation as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except psycopg2.Error as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except Exception as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

    def action_update_all_option(self):
        active_ids = self.env.context.get('active_ids', [])
        options = self.env['siantou.ems.core.option'].browse(active_ids)
        options = list(options)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')

        for option in options:
            self.update_option(option)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def write(self, vals):
        options = []
        if len(self.ids) == 1:
            option = self.env['siantou.ems.core.option'].browse(self.id)
            options.append(option)
        else:
            options = self.env['siantou.ems.core.option'].browse(self.ids)
            options = list(options)

        res = super(OptionOfStudy, self).write(vals)

        if ('name' in vals and vals['name'] and vals['name'].strip()) or ('option_name' in vals and vals['option_name'] and vals['option_name'].strip()):
            for option in options:
                classes = self.env['siantou.ems.core.class'].search([
                    ('option_id', '=', option.id),
                ])
                classes = list(classes)
                for classe in classes:
                    classe.write({
                        'option_id': option.id,
                    })

        return res


class SpecialtyOfStudy(models.Model):
    _name = 'siantou.ems.core.specialty'
    _description = 'Spécialité'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        string='Filière',
        required=True,
    )

    school_id = fields.Many2one(
        'siantou.ems.core.school',
        string='École',
        related='field_of_study_id.school_id'
    )

    cycle_id = fields.Many2one(
        'oe.school.course',
        string='Cursus ou Cycle',
        related='field_of_study_id.cycle_id'
    )

    supervision_id = fields.Many2one(
        'oe.school.course.supervision',
        string='Tutelle académique',
        related='cycle_id.supervision_id'
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Département'
    )

    code = fields.Char(
        string='Code',
        required=True
    )

    name = fields.Char(
        string='Nom',
        required=True
    )

    specialty_name = fields.Char(
        string='Nom',
        required=True
    )

    name = fields.Char(
        string='Nom de la spécialité',
        compute='_compute_name',
        store=True,
    )

    @api.depends('specialty_name', 'supervision_id')
    def _compute_name(self):
        for record in self:
            specialty_name = record.specialty_name if record.specialty_name else ''
            specialty_name = specialty_name.lower()
            while True:
                if specialty_name.find('-') != -1:
                    specialty_name = specialty_name.replace('-', ' ')
                else:
                    break
            supervision_name = record.supervision_id.name if record.supervision_id.id else ''
            if supervision_name != '':
                supervision_name = f'- {supervision_name}'
            supervisions = self.env['oe.school.course.supervision'].search([])
            supervisions = list(supervisions)
            for supervision in supervisions:
                name = supervision.name
                name = name.lower()
                while True:
                    if specialty_name.find(name) != -1:
                        specialty_name = specialty_name.replace(name, '')
                    else:
                        break
                names = name.split('/')
                for name in names:
                    while True:
                        if specialty_name.find(name) != -1:
                            specialty_name = specialty_name.replace(name, '')
                        else:
                            break
            name = '{} {}'.format(specialty_name, supervision_name)
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

    @api.onchange('specialty_name', 'supervision_id')
    def _onchange_name(self):
        for record in self:
            record._compute_name()

    option_ids = fields.One2many(
        'siantou.ems.core.option',
        'specialty_id',
        'Options'
    )

    slot_id = fields.Many2one(
        'siantou.ems.timetable.slot',
        string='Créneau horaire',
    )

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code de la spécialité doit être unique.'),
    ]

    def update_specialty(self, specialty):
        try:
            specialty_name = specialty.name if specialty.name else ''
            specialty_name = specialty_name.lower()
            while True:
                if specialty_name.find('-') != -1:
                    specialty_name = specialty_name.replace('-', ' ')
                else:
                    break
            supervisions = self.env['oe.school.course.supervision'].search([])
            supervisions = list(supervisions)
            for supervision in supervisions:
                name = supervision.name
                name = name.lower()
                while True:
                    if specialty_name.find(name) != -1:
                        specialty_name = specialty_name.replace(name, '')
                    else:
                        break
                names = name.split('/')
                for name in names:
                    while True:
                        if specialty_name.find(name) != -1:
                            specialty_name = specialty_name.replace(name, '')
                        else:
                            break
            name = specialty_name
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            specialty.write({
                'specialty_name': name,
            })
        except psycopg2.errors.NotNullViolation as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except psycopg2.Error as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except Exception as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

    def action_update_all_specialty(self):
        active_ids = self.env.context.get('active_ids', [])
        specialties = self.env['siantou.ems.core.specialty'].browse(active_ids)
        specialties = list(specialties)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')

        for specialty in specialties:
            self.update_specialty(specialty)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def write(self, vals):
        specialties = []
        if len(self.ids) == 1:
            specialty = self.env['siantou.ems.core.specialty'].browse(self.id)
            specialties.append(specialty)
        else:
            specialties = self.env['siantou.ems.core.specialty'].browse(self.ids)
            specialties = list(specialties)

        res = super(SpecialtyOfStudy, self).write(vals)

        if ('name' in vals and vals['name'] and vals['name'].strip()) or ('specialty_name' in vals and vals['specialty_name'] and vals['specialty_name'].strip()):
            for specialty in specialties:
                classes = self.env['siantou.ems.core.class'].search([
                    ('specialty_id', '=', specialty.id),
                ])
                classes = list(classes)
                for classe in classes:
                    classe.write({
                        'specialty_id': specialty.id,
                    })

        return res


class FieldOfStudy(models.Model):
    _name = 'siantou.ems.core.field_of_study'
    _description = 'Filière'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    code = fields.Char(
        string='Code',
        required=True
    )

    field_of_study_name = fields.Char(
        string='Nom',
        required=True
    )

    name = fields.Char(
        string='Nom de la filière',
        compute='_compute_name',
        store=True,
    )

    @api.depends('field_of_study_name', 'supervision_id')
    def _compute_name(self):
        for record in self:
            field_of_study_name = record.field_of_study_name if record.field_of_study_name else ''
            field_of_study_name = field_of_study_name.lower()
            while True:
                if field_of_study_name.find('-') != -1:
                    field_of_study_name = field_of_study_name.replace('-', ' ')
                else:
                    break
            supervision_name = record.supervision_id.name if record.supervision_id else ''
            if supervision_name != '':
                supervision_name = f'- {supervision_name}'
            supervisions = self.env['oe.school.course.supervision'].search([])
            supervisions = list(supervisions)
            for supervision in supervisions:
                name = supervision.name
                name = name.lower()
                while True:
                    if field_of_study_name.find(name) != -1:
                        field_of_study_name = field_of_study_name.replace(name, '')
                    else:
                        break
                names = name.split('/')
                for name in names:
                    while True:
                        if field_of_study_name.find(name) != -1:
                            field_of_study_name = field_of_study_name.replace(name, '')
                        else:
                            break
            name = '{} {}'.format(field_of_study_name, supervision_name)
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

    @api.onchange('field_of_study_name', 'supervision_id')
    def _onchange_name(self):
        for record in self:
            record._compute_name()

    school_id = fields.Many2one(
        'siantou.ems.core.school',
        string='École',
    )

    cycle_id = fields.Many2one(
        'oe.school.course',
        string='Cursus ou Cycle',
    )

    supervision_id = fields.Many2one(
        'oe.school.course.supervision',
        string='Tutelle académique',
        related='cycle_id.supervision_id'
    )

    specialty_ids = fields.One2many(
        'siantou.ems.core.specialty',
        'field_of_study_id',
        'Spécialités'
    )

    batch_ids = fields.One2many(
        'siantou.ems.core.student.batch',
        'field_of_study_id',
        string='Lots de la filière'
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Département'
    )

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code de la filière doit être unique.'),
    ]

    def get_subject_ids_by_level(self):
        # Dictionnaire pour stocker les IDs des cours par niveau
        subject_ids_by_level = {}

        # Parcourt tous les niveaux de la filière
        levels = self.env['siantou.ems.core.level'].search([])
        levels = list(levels)
        for level in levels:
            subject_ids_by_level[level.id] = []
            # Filtre les cours de cette filière et de ce niveau
            classes = self.env['siantou.ems.core.class'].search([
                ('level_id', '=', level.id),
                ('field_of_study_id', '=', self.id)
            ])
            classes = list(classes)
            for classe in classes:
                subjects = self.env['siantou.ems.core.subject'].search([
                    ('ue_ids', 'in', classe.ue_ids.ids),
                ])
                subjects = list(subjects)
                for subject in subjects:
                    if subject.id not in subject_ids_by_level[level.id]:
                        subject_ids_by_level[level.id].append(subject.id)
            if len(subject_ids_by_level[level.id]) == 0:
                del(subject_ids_by_level[level.id])

        return subject_ids_by_level

    def update_field_of_study(self, field_of_study):
        try:
            field_of_study_name = field_of_study.name if field_of_study.name else ''
            field_of_study_name = field_of_study_name.lower()
            while True:
                if field_of_study_name.find('-') != -1:
                    field_of_study_name = field_of_study_name.replace('-', ' ')
                else:
                    break
            supervisions = self.env['oe.school.course.supervision'].search([])
            supervisions = list(supervisions)
            for supervision in supervisions:
                name = supervision.name
                name = name.lower()
                while True:
                    if field_of_study_name.find(name) != -1:
                        field_of_study_name = field_of_study_name.replace(name, '')
                    else:
                        break
                names = name.split('/')
                for name in names:
                    while True:
                        if field_of_study_name.find(name) != -1:
                            field_of_study_name = field_of_study_name.replace(name, '')
                        else:
                            break
            name = field_of_study_name
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            field_of_study.write({
                'field_of_study_name': name,
            })
        except psycopg2.errors.NotNullViolation as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except psycopg2.Error as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except Exception as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

    def action_update_all_field_of_study(self):
        active_ids = self.env.context.get('active_ids', [])
        field_of_studies = self.env['siantou.ems.core.field_of_study'].browse(active_ids)
        field_of_studies = list(field_of_studies)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')

        for field_of_study in field_of_studies:
            self.update_field_of_study(field_of_study)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
