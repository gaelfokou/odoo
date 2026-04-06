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

class Subject(models.Model):
    _name = 'siantou.ems.core.subject'
    _description = 'Cour'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    # Code du cours
    code = fields.Char(
        'Code',
        required=True
    )

    # Variable booléenne pour savoir si c'est un tronc commun ou pas
    shared_subject = fields.Boolean(
        'Tronc commun',
        default=False
    )

    subject_parent_ids = fields.Many2many(
        'siantou.ems.core.subject',
        'subject_parent_child_rel',
        'subject_child_id',
        'subject_parent_id',
        string='Cours parent',
        domain="[('shared_subject', '=', False)]",
    )

    subject_child_ids = fields.Many2many(
        'siantou.ems.core.subject',
        'subject_parent_child_rel',
        'subject_parent_id',
        'subject_child_id',
        string='Cours enfant',
        domain="[('shared_subject', '=', True)]",
    )

    # Variable booléenne pour savoir si c'est une matière fait partie de l'EPS ou pas
    eps_subject = fields.Boolean(
        'Mathière de l\'EPS',
        default=False
    )

    # Nom du cours
    name = fields.Char(
        string='Nom',
        required=True
    )

    # Volume horaire du cours sur un semestre
    hours_credit = fields.Float(
        'Volume horaire',
        help='Volume horaire du cours sur un semestre',
        default=0.0,
        required=True
    )

    ue_ids = fields.Many2many('siantou.ems.core.unite.enseignement', 'ue_subject_rel', 'subject_id', 'ue_id', string='Unités d\'enseignement')

    syllabus_ids = fields.One2many('siantou.ems.core.syllabus', 'subject_id', string='Syllabus')

    # Les enseignants qui dispensent ce cours
    teacher_ids = fields.Many2many(
        'hr.employee',
        'teacher_subject_rel',
        'subject_id',
        'employee_id',
        string='Enseignants',
        # compute='_compute_teacher_ids',
        # inverse='_set_teacher_ids'
    )

    # Les priorités de chaque enseignant sur ce cours
    teacher_priority_ids = fields.One2many(
        'siantou.ems.core.teacher.subject.priority',
        'subject_id',
        'Priorités des enseignants'
    )

    total_credit = fields.Integer(
        string='Crédit total',
        compute='_compute_credit',
        store=True,
    )

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code du cours doit être unique.'),
    ]

    @api.constrains('subject_child_ids')
    def _check_subject_child_ids(self):
        for record in self:
            if record.shared_subject and len(record.subject_child_ids.ids) == 0:
                raise ValidationError("Les cours en tronc commun doivent être ajoutés")

    @api.onchange('shared_subject')
    def _onchange_shared_subject(self):
        for record in self:
            record.subject_child_ids = []

    @api.constrains('hours_credit')
    def _check_hours_credit(self):
        for record in self:
            if record.hours_credit <= 0:
                raise ValidationError("Le volume horaire semestriel doit être supérieur à 0")

    # Méthode calculée pour teacher_ids afin de montrer les enseignants liés dans le modèle des priorités
    # @api.depends('teacher_priority_ids')
    # def _compute_teacher_ids(self):
    #     for record in self:
    #         record.teacher_ids = record.teacher_priority_ids.mapped('employee_id')

    # Méthode inverse pour ajouter/supprimer des enseignants dans le modèle des priorités avec une priorité par défaut de 1
    # def _set_teacher_ids(self):
    #     for record in self:
    #         current_teacher_ids = record.teacher_priority_ids.mapped('employee_id').ids
    #         new_teacher_ids = record.teacher_ids.ids

    #         # Ajouter les nouveaux enseignants avec une priorité par défaut de 1
    #         to_add = set(new_teacher_ids) - set(current_teacher_ids)
    #         for teacher_id in to_add:
    #             self.env['siantou.ems.core.teacher.subject.priority'].create({
    #                 'employee_id': teacher_id,
    #                 'subject_id': record.id,
    #                 'priority': 1,
    #             })

    #         # Supprimer les enseignants enlevés de teacher_ids
    #         to_remove = set(current_teacher_ids) - set(new_teacher_ids)
    #         record.teacher_priority_ids.filtered(lambda p: p.employee_id.id in to_remove).unlink()

    @api.depends('syllabus_ids.subject_credit')
    def _compute_credit(self):
        for record in self:
            total = 0
            # On récupère tous les syllabus liés à cette sous matière
            syllabuses = self.env['siantou.ems.core.syllabus'].search([
                ('subject_id', '=', record.id)
            ])

            # Additionner les crédits de chaque syllabus
            for syllabus in syllabuses:
                total += syllabus.subject_credit

            record.total_credit = total

    def update_teacher_priority(self, subject):
        try:
            teacher_ids = subject.teacher_ids.ids
            exist_teacher_ids = []
            for teacher_priority_id in subject.teacher_priority_ids:
                if teacher_priority_id.employee_id.id not in teacher_ids:
                    teacher_priority_id.unlink()
                else:
                    exist_teacher_ids.append(teacher_priority_id.employee_id.id)
            exist_teacher_ids = list(set(exist_teacher_ids))
            for teacher_id in subject.teacher_ids:
                if teacher_id.id not in exist_teacher_ids:
                    subject.teacher_priority_ids.create({
                        'employee_id': teacher_id.id,
                        'subject_id': subject.id,
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
        subject = super(Subject, self).create(vals)

        self.update_teacher_priority(subject)

        return subject

    def write(self, vals):
        subject = self.env['siantou.ems.core.subject'].search([('id', '=', self.id)], limit=1)

        res = super(Subject, self).write(vals)

        self.update_teacher_priority(subject)

        return res

    def action_open_filter(self):
        view_id = self.env.ref('siantou_ems_core.subject_filter_wizard').id
        return {
            'name': 'Filtre des cours',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'subject.filter.wizard',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': {
                'default_year_id': self.env['siantou.ems.core.year'].search([('is_active', '=', True)], limit=1).id,
            },
        }

    def action_reset_filter(self):
        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', '')
        action = self.env.ref('siantou_ems_core.action_show_subject').read()[0]
        action.update({
            'target': 'main',
        })
        return action

    def action_print_pdf(self):
        active_ids = self.env.context.get('active_ids', [])
        subjects = self.env['siantou.ems.core.subject'].browse(active_ids)
        subjects = list(subjects)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')
        report_data = self.env['subject.print.wizard'].create({})
        domains = [
            ('id', 'in', active_ids)
        ]
        data = report_data.print_subject_report_data(domains=domains)

        if len(data['docdata']['subject_data']) == 0:
            raise UserError('Aucune donnée trouvée')
        report_action = self.env.ref('siantou_ems_core.action_report_subject')
        report_action.update({
            'name': 'Cours PDF',
        })
        return report_action.report_action(self, data=data)

class ProgressReport(models.Model):
    _name = 'siantou.ems.core.progress.report'
    _description = 'Fiche de progression'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    name = fields.Char(
        string='Nom',
        compute='_compute_name',
        store=True,
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

    session_ids = fields.One2many(
        'siantou.ems.core.subject.session',
        'report_id',
        'Séances de cours'
    )

    percentage = fields.Float(compute='_compute_percentage', store=True, string='Taux de consommation du volume horaire')

    _sql_constraints = [
        ('unique_class_subject', 'unique(class_id, subject_id)', 'Un cours ne peut être lié à une même classe qu\'une seule fois.')
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

    @api.depends('class_id', 'subject_id')
    def _compute_percentage(self):
        for record in self:
            search_domain = []
            search_domain.append(('class_id', '=', record.class_id.id))
            search_domain.append(('subject_id', '=', record.subject_id.id))

            search_domain.append('|')
            search_domain.append('&')
            search_domain.append('&')
            search_domain.append(('group_id.is_active', '=', True))
            search_domain.append(('group_id.is_submit', '=', False))
            search_domain.append(('group_id.status', '=', 'valid'))
            search_domain.append('&')
            search_domain.append('&')
            search_domain.append('&')
            search_domain.append(('group_parent_id.is_active', '=', True))
            search_domain.append(('group_parent_id.is_submit', '=', False))
            search_domain.append(('group_parent_id.status', '=', 'valid'))
            search_domain.append(('group_id.status', '=', 'valid'))
            search_domain.append(('is_active', '=', True))

            search_domain.append(('employee_id.is_teacher', '=', True))

            order = 'date asc, id asc'

            search_progressreports = self.env['siantou.ems.timetable.timetable'].search(search_domain, order=order).sorted(lambda rec: (rec.date, rec.id))
            search_progressreports = list(search_progressreports)
            data = []
            key_progressreports = {}
            for search_progressreport in search_progressreports:
                if not search_progressreport.date or not search_progressreport.day_of_week or not search_progressreport.employee_id.id:
                    continue

                end_time = ProgressReport.convert_float_to_time(search_progressreport.end_time)
                start_time = ProgressReport.convert_float_to_time(search_progressreport.start_time)
                key = '{}-{}-{}-{}'.format(search_progressreport.class_id.id, search_progressreport.date, start_time, end_time)
                if key not in key_progressreports:
                    key_progressreports[key] = search_progressreport
                else:
                    continue

                progressreport = {}
                progressreport['id'] = search_progressreport.id
                progressreport['name'] = search_progressreport.name
                progressreport['date'] = search_progressreport.date
                progressreport['date_of_week'] = datetime.strftime(search_progressreport.date, DATE_FORMAT_FR)
                progressreport['semester_name'] = search_progressreport.semester_id.name
                progressreport['cycle_name'] = search_progressreport.cycle_id.name
                progressreport['level_name'] = search_progressreport.level_id.name
                progressreport['field_of_study_id'] = search_progressreport.field_of_study_id.id
                progressreport['field_of_study_name'] = search_progressreport.field_of_study_id.name
                progressreport['specialty_name'] = search_progressreport.specialty_id.name
                progressreport['option_name'] = search_progressreport.option_id.name
                progressreport['class_id'] = search_progressreport.class_id.id
                progressreport['class_name'] = search_progressreport.class_id.name
                progressreport['department_id'] = search_progressreport.department_id.id
                progressreport['department_name'] = search_progressreport.department_id.name
                progressreport['subject_id'] = search_progressreport.subject_id.id
                progressreport['subject_name'] = search_progressreport.subject_id.name
                progressreport['subject_code'] = search_progressreport.subject_id.code
                progressreport['subject_hours_credit'] = search_progressreport.subject_id.hours_credit
                progressreport['subject_shared_subject'] = search_progressreport.subject_id.shared_subject
                progressreport['classroom_name'] = search_progressreport.classroom_id.name
                progressreport['building_name'] = search_progressreport.classroom_id.building_id.name
                progressreport['batch_name'] = search_progressreport.batch_id.name
                progressreport['employee_name'] = search_progressreport.employee_id.name
                progressreport['day_of_week'] = CURRENT_WEEKDAY[search_progressreport.day_of_week]
                progressreport['start_time'] = search_progressreport.start_time
                progressreport['end_time'] = search_progressreport.end_time
                progressreport['worked_start_time'] = search_progressreport.worked_start_time
                progressreport['worked_end_time'] = search_progressreport.worked_end_time
                progressreport['not_active_slotitems'] = search_progressreport.not_active_slotitems
                progressreport['status'] = search_progressreport.status
                session_ids = search_progressreport.session_ids
                session_ids = list(session_ids)
                sessions = []
                for session_id in session_ids:
                    session = {}
                    session['id'] = session_id.id
                    session['name'] = session_id.name
                    session['description'] = session_id.description
                    session['timetable_id'] = session_id.timetable_id.id
                    session['report_id'] = session_id.report_id.id
                    sessions.append(session)
                sessions = sorted(sessions, key=lambda item: int((item['name'] if item['name'] else '').replace('Séance ', '')))
                progressreport['sessions'] = sessions

                data.append(progressreport)

            progressreports = {}

            sorted_data = copy.deepcopy(data)

            for d in sorted_data:
                key_class = '{}'.format(d['class_id'])
                key_subject = '{}'.format(d['subject_id'])
                if key_class not in progressreports:
                    progressreports[key_class] = {}
                    progressreports[key_class]['name'] = d['class_name']
                    progressreports[key_class]['data'] = {}
                    progressreports[key_class]['data'][key_subject] = {}
                    progressreports[key_class]['data'][key_subject]['name'] = d['subject_name']
                    progressreports[key_class]['data'][key_subject]['data'] = []
                    progressreports[key_class]['data'][key_subject]['data'].append(d)
                else:
                    if key_subject not in progressreports[key_class]['data']:
                        progressreports[key_class]['data'][key_subject] = {}
                        progressreports[key_class]['data'][key_subject]['name'] = d['subject_name']
                        progressreports[key_class]['data'][key_subject]['data'] = []
                        progressreports[key_class]['data'][key_subject]['data'].append(d)
                    else:
                        progressreports[key_class]['data'][key_subject]['data'].append(d)

            for key_class in progressreports.keys():
                for key_subject in progressreports[key_class]['data'].keys():
                    subjectsessions = ProgressReport.format_subjectsession(progressreports[key_class]['data'][key_subject]['data'])
                    percentage_session = None
                    for key_timetable in subjectsessions.keys():
                        if subjectsessions[key_timetable]['status'] == 'Effectué':
                            for d in subjectsessions[key_timetable]['data']:
                                if not percentage_session:
                                    percentage_session = d['percentage']
                                else:
                                    if d['percentage'] > percentage_session:
                                        percentage_session = d['percentage']

                    if percentage_session:
                        progressreports[key_class]['data'][key_subject]['percentage'] = percentage_session
                    else:
                        progressreports[key_class]['data'][key_subject]['percentage'] = 0.0

                    record.percentage = progressreports[key_class]['data'][key_subject]['percentage']

    @api.onchange('class_id', 'subject_id')
    def _onchange_percentage(self):
        for record in self:
            search_domain = []
            search_domain.append(('class_id', '=', record.class_id.id))
            search_domain.append(('subject_id', '=', record.subject_id.id))

            search_domain.append('|')
            search_domain.append('&')
            search_domain.append('&')
            search_domain.append(('group_id.is_active', '=', True))
            search_domain.append(('group_id.is_submit', '=', False))
            search_domain.append(('group_id.status', '=', 'valid'))
            search_domain.append('&')
            search_domain.append('&')
            search_domain.append('&')
            search_domain.append(('group_parent_id.is_active', '=', True))
            search_domain.append(('group_parent_id.is_submit', '=', False))
            search_domain.append(('group_parent_id.status', '=', 'valid'))
            search_domain.append(('group_id.status', '=', 'valid'))
            search_domain.append(('is_active', '=', True))

            search_domain.append(('employee_id.is_teacher', '=', True))

            order = 'date asc, id asc'

            search_progressreports = self.env['siantou.ems.timetable.timetable'].search(search_domain, order=order).sorted(lambda rec: (rec.date, rec.id))
            search_progressreports = list(search_progressreports)
            data = []
            key_progressreports = {}
            for search_progressreport in search_progressreports:
                if not search_progressreport.date or not search_progressreport.day_of_week or not search_progressreport.employee_id.id:
                    continue

                end_time = ProgressReport.convert_float_to_time(search_progressreport.end_time)
                start_time = ProgressReport.convert_float_to_time(search_progressreport.start_time)
                key = '{}-{}-{}-{}'.format(search_progressreport.class_id.id, search_progressreport.date, start_time, end_time)
                if key not in key_progressreports:
                    key_progressreports[key] = search_progressreport
                else:
                    continue

                progressreport = {}
                progressreport['id'] = search_progressreport.id
                progressreport['name'] = search_progressreport.name
                progressreport['date'] = search_progressreport.date
                progressreport['date_of_week'] = datetime.strftime(search_progressreport.date, DATE_FORMAT_FR)
                progressreport['semester_name'] = search_progressreport.semester_id.name
                progressreport['cycle_name'] = search_progressreport.cycle_id.name
                progressreport['level_name'] = search_progressreport.level_id.name
                progressreport['field_of_study_id'] = search_progressreport.field_of_study_id.id
                progressreport['field_of_study_name'] = search_progressreport.field_of_study_id.name
                progressreport['specialty_name'] = search_progressreport.specialty_id.name
                progressreport['option_name'] = search_progressreport.option_id.name
                progressreport['class_id'] = search_progressreport.class_id.id
                progressreport['class_name'] = search_progressreport.class_id.name
                progressreport['department_id'] = search_progressreport.department_id.id
                progressreport['department_name'] = search_progressreport.department_id.name
                progressreport['subject_id'] = search_progressreport.subject_id.id
                progressreport['subject_name'] = search_progressreport.subject_id.name
                progressreport['subject_code'] = search_progressreport.subject_id.code
                progressreport['subject_hours_credit'] = search_progressreport.subject_id.hours_credit
                progressreport['subject_shared_subject'] = search_progressreport.subject_id.shared_subject
                progressreport['classroom_name'] = search_progressreport.classroom_id.name
                progressreport['building_name'] = search_progressreport.classroom_id.building_id.name
                progressreport['batch_name'] = search_progressreport.batch_id.name
                progressreport['employee_name'] = search_progressreport.employee_id.name
                progressreport['day_of_week'] = CURRENT_WEEKDAY[search_progressreport.day_of_week]
                progressreport['start_time'] = search_progressreport.start_time
                progressreport['end_time'] = search_progressreport.end_time
                progressreport['worked_start_time'] = search_progressreport.worked_start_time
                progressreport['worked_end_time'] = search_progressreport.worked_end_time
                progressreport['not_active_slotitems'] = search_progressreport.not_active_slotitems
                progressreport['status'] = search_progressreport.status
                session_ids = search_progressreport.session_ids
                session_ids = list(session_ids)
                sessions = []
                for session_id in session_ids:
                    session = {}
                    session['id'] = session_id.id
                    session['name'] = session_id.name
                    session['description'] = session_id.description
                    session['timetable_id'] = session_id.timetable_id.id
                    session['report_id'] = session_id.report_id.id
                    sessions.append(session)
                sessions = sorted(sessions, key=lambda item: int((item['name'] if item['name'] else '').replace('Séance ', '')))
                progressreport['sessions'] = sessions

                data.append(progressreport)

            progressreports = {}

            sorted_data = copy.deepcopy(data)

            for d in sorted_data:
                key_class = '{}'.format(d['class_id'])
                key_subject = '{}'.format(d['subject_id'])
                if key_class not in progressreports:
                    progressreports[key_class] = {}
                    progressreports[key_class]['name'] = d['class_name']
                    progressreports[key_class]['data'] = {}
                    progressreports[key_class]['data'][key_subject] = {}
                    progressreports[key_class]['data'][key_subject]['name'] = d['subject_name']
                    progressreports[key_class]['data'][key_subject]['data'] = []
                    progressreports[key_class]['data'][key_subject]['data'].append(d)
                else:
                    if key_subject not in progressreports[key_class]['data']:
                        progressreports[key_class]['data'][key_subject] = {}
                        progressreports[key_class]['data'][key_subject]['name'] = d['subject_name']
                        progressreports[key_class]['data'][key_subject]['data'] = []
                        progressreports[key_class]['data'][key_subject]['data'].append(d)
                    else:
                        progressreports[key_class]['data'][key_subject]['data'].append(d)

            for key_class in progressreports.keys():
                for key_subject in progressreports[key_class]['data'].keys():
                    subjectsessions = ProgressReport.format_subjectsession(progressreports[key_class]['data'][key_subject]['data'])
                    percentage_session = None
                    for key_timetable in subjectsessions.keys():
                        if subjectsessions[key_timetable]['status'] == 'Effectué':
                            for d in subjectsessions[key_timetable]['data']:
                                if not percentage_session:
                                    percentage_session = d['percentage']
                                else:
                                    if d['percentage'] > percentage_session:
                                        percentage_session = d['percentage']

                    if percentage_session:
                        progressreports[key_class]['data'][key_subject]['percentage'] = percentage_session
                    else:
                        progressreports[key_class]['data'][key_subject]['percentage'] = 0.0

                    record.percentage = progressreports[key_class]['data'][key_subject]['percentage']

    def action_open_filter(self):
        view_id = self.env.ref('siantou_ems_core.progress_report_filter_wizard').id
        return {
            'name': 'Filtre des fiches de progression',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'progress.report.filter.wizard',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': {
                'default_year_id': self.env['siantou.ems.core.year'].search([('is_active', '=', True)], limit=1).id,
            },
        }

    def action_reset_filter(self):
        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', '')
        action = self.env.ref('siantou_ems_core.action_show_progress_report').read()[0]
        action.update({
            'target': 'main',
        })
        return action

    def action_print_pdf(self):
        active_ids = self.env.context.get('active_ids', [])
        reports = self.env['siantou.ems.core.progress.report'].browse(active_ids)
        reports = list(reports)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')
        report_data = self.env['progress.report.print.wizard'].create({})
        domains = [
            ('id', 'in', active_ids)
        ]
        data = report_data.print_progress_report_data(domains=domains)

        if len(data['docdata']['report_data']) == 0:
            raise UserError('Aucune donnée trouvée')
        report_action = self.env.ref('siantou_ems_core.action_report_progress_report')
        report_action.update({
            'name': 'Fiches de progression PDF',
        })
        return report_action.report_action(self, data=data)

    def update_progress_report(self, report):
        try:
            report._compute_percentage()
            report.write({
                'class_id': report.class_id.id,
            })
            # self.env.cr.commit()
        except psycopg2.errors.NotNullViolation as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except psycopg2.Error as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except Exception as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

    def action_update_all_progress_report(self):
        active_ids = self.env.context.get('active_ids', [])
        reports = self.env['siantou.ems.core.progress.report'].browse(active_ids)
        reports = list(reports)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')

        for report in reports:
            self.update_progress_report(report)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def update_progress_report_class(self, report):
        try:
            year_id = self.env['siantou.ems.core.year'].search([('is_active', '=', True)], limit=1)
            if report.class_id.year_id.id != year_id.id:
                class_id = self.env['siantou.ems.core.class'].search([
                    ('name', '=', report.class_id.name),
                    ('year_id', '=', year_id.id),
                ], limit=1)
                if class_id:
                    report.write({
                        'class_id': class_id.id,
                    })
            # self.env.cr.commit()
        except psycopg2.errors.NotNullViolation as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except psycopg2.Error as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except Exception as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

    def action_update_all_progress_report_class(self):
        active_ids = self.env.context.get('active_ids', [])
        reports = self.env['siantou.ems.core.progress.report'].browse(active_ids)
        reports = list(reports)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')

        for report in reports:
            self.update_progress_report_class(report)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @staticmethod
    def format_subjectsession(data):
        subjectsessions = {}

        sorted_data = copy.deepcopy(data)

        percentage_session = sum([len(d['sessions']) for d in sorted_data])
        if percentage_session > 0:
            percentage_session = (1 / percentage_session) * 100
        else:
            percentage_session = 0.0
        percentage_session = round(percentage_session, 2)

        total_session = 0.0
        for d in sorted_data:
            key_timetable = '{}'.format(d['id'])
            if key_timetable not in subjectsessions:
                subjectsessions[key_timetable] = {}
                subjectsessions[key_timetable]['id'] = d['id']
                subjectsessions[key_timetable]['name'] = d['name']
                subjectsessions[key_timetable]['status'] = 'Effectué' if d['status'] in ['present', 'permission'] else 'En attente'
                subjectsessions[key_timetable]['class_id'] = d['class_id']
                subjectsessions[key_timetable]['class_name'] = d['class_name']
                subjectsessions[key_timetable]['subject_id'] = d['subject_id']
                subjectsessions[key_timetable]['subject_name'] = d['subject_name']
                subjectsessions[key_timetable]['date'] = d['date_of_week']
                subjectsessions[key_timetable]['start_time'] = ProgressReport.convert_float_to_time(d['start_time'])
                subjectsessions[key_timetable]['end_time'] = ProgressReport.convert_float_to_time(d['end_time'])
                for v in d['sessions']:
                    total_session += percentage_session
                    total_session = round(total_session, 2)
                    v['percentage'] = total_session if total_session <= 100.0 else 100.0
                subjectsessions[key_timetable]['data'] = d['sessions']

        _logger.info(f'----------- tototototototo subjectsessions {subjectsessions} -----------')

        return subjectsessions

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

class SubjectSession(models.Model):
    _name = 'siantou.ems.core.subject.session'
    _description = 'Séance de cours'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    name = fields.Char(
        string='Séance',
        # compute='_compute_name',
        # store=True,
    )

    description = fields.Text(
        'Description',
    )

    timetable_id = fields.Many2one(
        'siantou.ems.timetable.timetable',
        string='Emploi du temps',
        required=True,
        ondelete='cascade'
    )

    report_id = fields.Many2one(
        'siantou.ems.core.progress.report',
        'Fiche de progression',
        required=True,
        ondelete='cascade'
    )

    is_update = fields.Boolean('Mise à jour ?', default=False)

    timetable_id_domain = fields.Binary(compute='_compute_class_domain', default=[])

    @api.depends('timetable_id', 'report_id')
    def _compute_name(self):
        for record in self:
            sessions = self.env['siantou.ems.core.subject.session'].search([
                ('report_id', '=', record.report_id.id),
            ])
            sessions = list(sessions)
            sessions = len(sessions)
            name = 'Séance {}'.format(sessions)
            record.name = name

    @api.onchange('timetable_id', 'report_id')
    def _onchange_name(self):
        for record in self:
            sessions = self.env['siantou.ems.core.subject.session'].search([
                ('report_id', '=', record.report_id.id),
            ])
            sessions = list(sessions)
            sessions = len(sessions)
            name = 'Séance {}'.format(sessions)
            record.name = name

    @api.depends('report_id')
    def _compute_class_domain(self):
        for record in self:
            domain = []
            if record.report_id.id:
                timetable_ids = record.report_id.class_id.timetable_ids
                domain = [
                    ('id', 'in', timetable_ids.ids),
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
                    ('subject_id', '=', record.report_id.subject_id.id)
                ]
            record.timetable_id_domain = domain

    @api.onchange('report_id')
    def _onchange_school(self):
        for record in self:
            record.timetable_id = None

    def update_session_name(self, report):
        try:
            session_ids = report.session_ids
            session_ids = list(session_ids)
            session_ids = sorted(session_ids, key=lambda item: (item.timetable_id.date, item.timetable_id.id))
            for i, session_id in enumerate(session_ids):
                name = 'Séance {}'.format(i + 1)
                session_id.write({
                    'name': name,
                    'is_update': True,
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
        session = super(SubjectSession, self).create(vals)

        report = session.report_id
        self.update_session_name(report)

        return session

    def write(self, vals):
        session = self.env['siantou.ems.core.subject.session'].search([('id', '=', self.id)], limit=1)

        res = super(SubjectSession, self).write(vals)

        if 'is_update' not in vals or not vals['is_update']:
            report = session.report_id
            self.update_session_name(report)

        return res
