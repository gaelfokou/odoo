# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP
from datetime import date, datetime, timedelta, time
import re
import psycopg2
import copy
import logging

_logger = logging.getLogger(__name__)

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
    'delay': 'Retard',
}

class ExamScore(models.Model):
    _name = 'siantou.ems.core.exam.score'
    _description = 'Fiche d\'examen'

    name = fields.Char(
        string='Nom',
        compute='_compute_name',
        store=True,
    )

    year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année académique',
        required=True
    )

    semester_id = fields.Many2one(
        'siantou.ems.core.year.semester',
        string='Semestre',
        required=True
    )

    class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe',
        required=True,
        ondelete='cascade'
    )

    subject_id = fields.Many2one(
        'siantou.ems.core.subject',
        'Cours',
        required=True,
        ondelete='cascade'
    )

    score_ids = fields.One2many(
        'siantou.ems.core.subject.score',
        'exam_id',
        'Notes d\'examen'
    )

    exam_type = fields.Selection([
        ('cc', 'Contrôle continu'),
        ('sn', 'Session normale'),
        ('rcc', 'Rattrapage contrôle continu'),
        ('rsn', 'Rattrapage session normale'),
    ], 'Statut',
        default='cc',
    )

    # Contrainte SQL pour s'assurer de l'unicité du couple (classe, couple) dans la base de donnée
    _sql_constraints = [
        ('unique_class_subject_rel', 'unique(class_id, subject_id)', 'Un cours ne peut être lié à une même classe qu\'une seule fois.')
    ]

    subject_id_domain = fields.Binary(compute='_compute_class_domain', default=[])

    @api.depends('class_id', 'subject_id')
    def _compute_name(self):
        for record in self:
            class_name = record.class_id.name if record.class_id.id else ''
            subject_name = record.subject_id.name if record.subject_id.id else ''
            name = '{} - {}'.format(class_name, subject_name)
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

    @api.onchange('class_id', 'subject_id')
    def _onchange_name(self):
        for record in self:
            class_name = record.class_id.name if record.class_id.id else ''
            subject_name = record.subject_id.name if record.subject_id.id else ''
            name = '{} - {}'.format(class_name, subject_name)
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

class SubjectScore(models.Model):
    _name = 'siantou.ems.core.subject.score'
    _description = 'Note d\'examen'

    name = fields.Char(
        string='Nom',
        compute='_compute_name',
        store=True,
    )

    description = fields.Text(
        'Description',
    )

    student_id = fields.Many2one(
        'oe.school.student',
        string='Étudiant',
        required=True,
        ondelete='cascade'
    )

    exam_id = fields.Many2one(
        'siantou.ems.core.exam.score',
        'Fiche d\'examen',
        required=True,
        ondelete='cascade'
    )

    score = fields.Float(
        'Note',
        default=0.0,
    )

    student_id_domain = fields.Binary(compute='_compute_class_domain', default=[])

    @api.depends('student_id', 'exam_id')
    def _compute_name(self):
        for record in self:
            student_name = record.student_id.name if record.student_id.id else ''
            exam_name = record.exam_id.name if record.exam_id.id else ''
            name = '{} - {}'.format(student_name, exam_name)
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

    @api.onchange('student_id', 'exam_id')
    def _onchange_name(self):
        for record in self:
            student_name = record.student_id.name if record.student_id.id else ''
            exam_name = record.exam_id.name if record.exam_id.id else ''
            name = '{} - {}'.format(student_name, exam_name)
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

    @api.depends('exam_id')
    def _compute_class_domain(self):
        for record in self:
            domain = []
            if record.exam_id.id:
                student_ids = record.exam_id.class_id.student_ids
                domain = [
                    ('id', 'in', student_ids.ids),
                ]
            record.student_id_domain = domain
