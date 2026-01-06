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
    _inherit=['mail.thread', 'mail.activity.mixin',]

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
        string='Cours',
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

    status = fields.Selection([
        ('start', 'Début'),
        ('start_write', 'Début saisie'),
        ('end_write', 'Fin saisie'),
        ('end', 'Fin'),
    ], 'Statut',
        default='start',
    )

    state = fields.Selection([
        ('start', 'Début'),
        ('start_write', 'Début saisie'),
        ('end_write', 'Fin saisie'),
        ('end', 'Fin'),
    ], 'Statut',
        related='status',
        store=True,
        tracking=True
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

    def state_start_exam(self):
        self.write({
            'status': 'start',
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def state_start_write_exam(self):
        self.write({
            'status': 'start_write',
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def state_end_write_exam(self):
        self.write({
            'status': 'end_write',
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def state_end_exam(self):
        self.write({
            'status': 'end',
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def create_student_score(self, exam):
        try:
            if exam.exam_type in ['sn', 'rsn']:
                student_ids = exam.class_id.student_ids.ids
                exist_student_ids = []
                for score_id in exam.score_ids:
                    if score_id.student_id.id not in student_ids:
                        score_id.unlink()
                    else:
                        exist_student_ids.append(score_id.student_id.id)
                exist_student_ids = list(set(exist_student_ids))
                for student_id in exam.class_id.student_ids:
                    if student_id.id not in exist_student_ids:
                        exam.score_ids.create({
                            'exam_id': exam.id,
                            'student_id': student_id.id,
                        })
            # self.env.cr.commit()
        except psycopg2.errors.NotNullViolation as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except psycopg2.Error as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except Exception as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

    def update_student_score(self, exam):
        try:
            if exam.exam_type in ['sn', 'rsn']:
                for score_id in exam.score_ids:
                    score_id.write({
                        'student_id': score_id.student_id.id,
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
        exam = super(ExamScore, self).create(vals)

        self.create_student_score(exam)

        return exam

    def write(self, vals):
        exam = self.env['siantou.ems.core.exam.score'].search([('id', '=', self.id)], limit=1)

        res = super(ExamScore, self).write(vals)

        self.update_student_score(exam)

        return res

class SubjectScore(models.Model):
    _name = 'siantou.ems.core.subject.score'
    _description = 'Note d\'examen'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    name = fields.Char(
        string='Nom',
        compute='_compute_name',
        store=True,
    )

    exam_id = fields.Many2one(
        'siantou.ems.core.exam.score',
        'Fiche d\'examen',
        required=True,
        ondelete='cascade'
    )

    exam_type = fields.Selection([
        ('cc', 'Contrôle continu'),
        ('sn', 'Session normale'),
        ('rcc', 'Rattrapage contrôle continu'),
        ('rsn', 'Rattrapage session normale'),
    ], 'Statut',
        related='exam_id.exam_type',
        store=True
    )

    status = fields.Selection([
        ('start', 'Début'),
        ('start_write', 'Début saisie'),
        ('end_write', 'Fin saisie'),
        ('end', 'Fin'),
    ], 'Statut',
        related='exam_id.status',
        store=True
    )

    student_id = fields.Many2one(
        'oe.school.student',
        string='Étudiant',
        required=True,
        ondelete='cascade'
    )

    anonymous = fields.Char(string="Anonymat")

    score = fields.Float(
        'Note',
        default=0.0,
    )

    note = fields.Text(
        'Remarque',
    )

    student_id_domain = fields.Binary(compute='_compute_class_domain', default=[])

    @api.depends('student_id', 'anonymous', 'exam_id')
    def _compute_name(self):
        for record in self:
            if record.exam_id.exam_type in ['sn', 'rsn']:
                if record.exam_id.status in ['start_write', 'end_write']:
                    anonymous = record.anonymous if record.anonymous else ''
                    name = '{}'.format(anonymous)
                else:
                    anonymous = record.anonymous if record.anonymous else ''
                    student_name = record.student_id.name if record.student_id.id else ''
                    name = '{} - {}'.format(anonymous, student_name)
            else:
                student_name = record.student_id.name if record.student_id.id else ''
                name = '{}'.format(student_name)
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

    @api.onchange('student_id', 'anonymous', 'exam_id')
    def _onchange_name(self):
        for record in self:
            if record.exam_id.exam_type in ['sn', 'rsn']:
                if record.exam_id.status in ['start_write', 'end_write']:
                    anonymous = record.anonymous if record.anonymous else ''
                    name = '{}'.format(anonymous)
                else:
                    anonymous = record.anonymous if record.anonymous else ''
                    student_name = record.student_id.name if record.student_id.id else ''
                    name = '{} - {}'.format(anonymous, student_name)
            else:
                student_name = record.student_id.name if record.student_id.id else ''
                name = '{}'.format(student_name)
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

    def create_student_anonymous(self, score):
        try:
            if score.exam_type in ['sn', 'rsn']:
                exam_type = re.sub('[^A-Za-z]+', '', score.exam_type)
                exam_type = exam_type[:4]
                exam_type = exam_type.upper()
                if not score.anonymous or not score.anonymous.strip():
                    anonymous = exam_type + self.env['ir.sequence'].next_by_code('siantou.ems.core.subject.score')
                    while True:
                        score_id = self.env['siantou.ems.core.subject.score'].search([
                            ('id', '!=', score.id),
                            ('anonymous', '=', anonymous),
                        ], limit=1)
                        if score_id:
                            anonymous = exam_type + self.env['ir.sequence'].next_by_code('siantou.ems.core.subject.score')
                        else:
                            break
                else:
                    anonymous = score.anonymous
                    anonymous = '{}'.format(anonymous)
                score.write({
                    'anonymous': anonymous,
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
        score = super(SubjectScore, self).create(vals)

        self.create_student_anonymous(score)

        return score
