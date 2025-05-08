# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
import psycopg2
from odoo.tools import unique
import re
import logging

_logger = logging.getLogger(__name__)

class HourlyRate(models.Model):
    _name = 'siantou.ems.core.hourly.rate'
    _description = 'Taux horaire'

    name = fields.Char(string='Nom',
                       compute='_compute_name', store=True)

    school_id = fields.Many2one(
        'siantou.ems.core.school',
        string='Ecole',
        required=True,
        ondelete='cascade'
    )

    cycle_id = fields.Many2one(
        'oe.school.course',
        string='Cursus ou Cycle',
        required=True,
        ondelete='cascade'
    )

    level_id = fields.Many2one(
        'siantou.ems.core.level',
        'Niveau',
        required=True,
        ondelete='cascade'
    )

    # Taux horaire
    rate = fields.Float(
        'Taux horaire',
        help='Taux horaire',
        default=0,
        required=True
    )

    # Contrainte SQL pour empêcher d'avoir le même code pour différentes filières
    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code de la filière doit être unique.'),
    ]

    @api.depends('school_id', 'cycle_id', 'level_id')
    def _compute_name(self):
        for record in self:
            school_name = record.school_id.name if record.school_id.id else ''
            cycle_name = record.cycle_id.name if record.cycle_id.id else ''
            niveau_name = record.level_id.name if record.level_id.id else ''
            niveau_name = re.sub(r'Niveau ', '', niveau_name)
            name = '{} {} {}'.format(school_name, cycle_name, niveau_name)
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

    @api.onchange('school_id', 'cycle_id', 'level_id')
    def _onchange_name(self):
        for record in self:
            school_name = record.school_id.name if record.school_id.id else ''
            cycle_name = record.cycle_id.name if record.cycle_id.id else ''
            niveau_name = record.level_id.name if record.level_id.id else ''
            niveau_name = re.sub(r'Niveau ', '', niveau_name)
            name = '{} {} {}'.format(school_name, cycle_name, niveau_name)
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

class TeacherHourlyRate(models.Model):
    _name = 'siantou.ems.core.teacher.hourly.rate'
    _description = 'Taux horaire de l\'enseignant sur un cours'

    name = fields.Char(string='Nom',
                       compute='_compute_name', store=True)

    # Enseignant pour lequel on souhaite définir la priorité sur le cours
    employee_id = fields.Many2one(
        'hr.employee',
        'Enseignant',
        required=True,
        ondelete='cascade'
    )

    # Cours pour lequel on souhaite définir la priorité de l'enseignant
    subject_id = fields.Many2one(
        'siantou.ems.core.subject',
        'Cours',
        required=True,
        ondelete='cascade'
    )

    hourly_rate_id = fields.Many2one(
        'siantou.ems.core.hourly.rate',
        'Taux horaire',
        ondelete='cascade'
    )

    # Taux horaire de l\'enseignant
    rate = fields.Float(
        'Taux horaire',
        help='Taux horaire de l\'enseignant',
        default=0,
        required=True
    )

    # Contrainte SQL pour empêcher d'avoir le même code pour différentes filières
    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code de la filière doit être unique.'),
    ]

    @api.depends('employee_id', 'subject_id')
    def _compute_name(self):
        for record in self:
            employee_name = record.employee_id.name if record.employee_id.id else ''
            subject_name = record.subject_id.name if record.subject_id.id else ''
            name = '{} {}'.format(employee_name, subject_name)
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

    @api.onchange('employee_id', 'subject_id')
    def _onchange_name(self):
        for record in self:
            employee_name = record.employee_id.name if record.employee_id.id else ''
            subject_name = record.subject_id.name if record.subject_id.id else ''
            name = '{} {}'.format(employee_name, subject_name)
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

    @api.onchange('hourly_rate_id')
    def _onchange_name(self):
        for record in self:
            record.rate = record.hourly_rate_id.rate
