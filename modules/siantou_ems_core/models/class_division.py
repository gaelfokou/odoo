# -*- coding: utf-8 -*-

import re
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
import psycopg2
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
from odoo.tools import unique
import logging

DATE_FORMAT = '%Y-%m-%d'
DATE_FORMAT_FR = '%d/%m/%Y'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATETIME_FORMAT_FR = '%d/%m/%Y %H:%M'
TIME_FORMAT = '%H:%M:%S'
TIME_FORMAT_FR = '%H:%M'

TYPE_COUR = {
    'cj': 'Cours du jour',
    'cs': 'Cours du soir',
}

_logger = logging.getLogger(__name__)


class EducationClass(models.Model):
    _name = 'siantou.ems.core.class'
    _description = 'Classe'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    name = fields.Char(string='Nom',
                       compute='_compute_name',
                       store=True,
                       help="Entrer le nom de la Classe")

    field_of_study_id = fields.Many2one('siantou.ems.core.field_of_study', string='Filière',
                                 required=True, help="Filière")

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

    student_enroll_ids = fields.One2many(
        'oe.school.student.enrollment',
        'class_id',
        string='Étudiants inscrits',
    )

    student_ids = fields.One2many(
        'oe.school.student',
        string='Étudiants',
        compute='_compute_students_call'
    )

    delegate_student_ids = fields.Many2many(
        'oe.school.student',
        'delegate_class_student_rel',
        'delegate_class_id',
        'delegate_student_id',
        string='Délégués de classe',
    )

    number_of_student = fields.Integer(
        string='Nombre d\'étudiants',
        compute='_compute_students_call',
        store=True,
    )

    timetable_ids = fields.One2many(
        'siantou.ems.timetable.timetable',
        string='Emplois du temps',
        compute='_compute_timetables'
    )

    number_of_hours = fields.Float(
        string='Nombre d\'heures programmées',
        compute='_compute_hours_call',
        store=True,
    )

    number_of_worked_hours = fields.Float(
        string='Nombre d\'heures effectuées',
        compute='_compute_hours_call',
        store=True,
    )

    specialty_id = fields.Many2one('siantou.ems.core.specialty', string='Spécialité',
                                 required=True, help="Spécialité")

    department_id = fields.Many2one(
        'hr.department',
        string='Département',
        related='specialty_id.department_id'
    )

    option_id = fields.Many2one('siantou.ems.core.option', string='Option',
                                 help="Option")

    level_id = fields.Many2one('siantou.ems.core.level', string='Niveau',
                                 required=True, help="Niveau")

    school_id = fields.Many2one('siantou.ems.core.school', string='École', required=True)

    year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année académique',
        default=lambda self: self.env['siantou.ems.core.year'].search([('is_active', '=', True)], limit=1),
        required=True
    )

    ue_ids = fields.Many2many('siantou.ems.core.unite.enseignement', 'class_ue_rel', 'class_id', 'ue_id', string='Unités d\'enseignement')

    group_ids = fields.Many2many('siantou.ems.timetable.group', 'class_group_rel', 'class_id', 'group_id', string='Versions d\'emploi du temps')

    subject_ids = fields.One2many(
        'siantou.ems.core.subject',
        string='Cours',
        compute='_compute_subjects'
    )

    number_of_subjects = fields.Integer(
        string='Nombre de cours',
        compute='_compute_subjects_call',
    )

    min_hours_credit = fields.Float(
        string='Volume horaire min',
        compute='_compute_hours_credit_call',
        store=True,
    )

    max_hours_credit = fields.Float(
        string='Volume horaire max',
        compute='_compute_hours_credit_call',
        store=True,
    )

    semester_id = fields.Many2one(
        'siantou.ems.core.year.semester',
        string='Semestre',
        compute='_compute_hours_credit_call',
    )

    start_date = fields.Date(
        string="Date de début",
        compute='_compute_date_call',
    )

    end_date = fields.Date(
        string="Date de fin",
        compute='_compute_date_call',
    )

    @api.depends('year_id', 'semester_id')
    def _compute_date_call(self):
        for record in self:
            if record.semester_id.id:
                record.start_date = record.semester_id.start_time
                record.end_date = record.semester_id.end_time
            else:
                if record.year_id.id:
                    record.start_date = record.year_id.start_time
                    record.end_date = record.year_id.end_time
                else:
                    record.start_date = None
                    record.end_date = None

    @api.onchange('year_id', 'semester_id')
    def _onchange_date_call(self):
        for record in self:
            record._compute_date_call()

    @api.depends('subject_ids', 'timetable_ids')
    def _compute_hours_credit_call(self):
        for record in self:
            record._compute_min_hours_credit()
            record._compute_max_hours_credit()
            record._compute_semester()

    @api.onchange('subject_ids', 'timetable_ids')
    def _onchange_hours_credit_call(self):
        for record in self:
            record._compute_hours_credit_call()

    def _compute_min_hours_credit(self):
        for record in self:
            semester_user = self.env['ir.config_parameter'].sudo().get_param(f'siantou.semester_user_{self.env.user.id}', '')
            if semester_user:
                record.min_hours_credit = 420.0
            else:
                record.min_hours_credit = 420.0 * 2

    def _compute_max_hours_credit(self):
        for record in self:
            semester_user = self.env['ir.config_parameter'].sudo().get_param(f'siantou.semester_user_{self.env.user.id}', '')
            if semester_user:
                record.max_hours_credit = 450.0
            else:
                record.max_hours_credit = 450.0 * 2

    def _compute_semester(self):
        for record in self:
            semester_user = self.env['ir.config_parameter'].sudo().get_param(f'siantou.semester_user_{self.env.user.id}', '')
            if semester_user:
                semester_user = int(semester_user)
                semester = self.env['siantou.ems.core.year.semester'].search([('id', '=', semester_user)], limit=1)
                if semester:
                    record.semester_id = semester
                else:
                    record.semester_id = None
            else:
                record.semester_id = None

    subjects_validated_ids = fields.One2many(
        'siantou.ems.core.subject',
        string='Cours validés',
        compute='_compute_subjects_call'
    )

    number_of_subjects_validated = fields.Integer(
        string='Nombre de cours validés',
        compute='_compute_subjects_call',
    )

    subjects_not_validated_ids = fields.One2many(
        'siantou.ems.core.subject',
        string='Cours non validés',
        compute='_compute_subjects_call'
    )

    number_of_subjects_not_validated = fields.Integer(
        string='Nombre de cours non validés',
        compute='_compute_subjects_call',
    )

    subjects_submitted_ids = fields.One2many(
        'siantou.ems.core.subject',
        string='Cours soumis',
        compute='_compute_subjects_call'
    )

    number_of_subjects_submitted = fields.Integer(
        string='Nombre de cours soumis',
        compute='_compute_subjects_call',
    )

    subjects_not_submitted_ids = fields.One2many(
        'siantou.ems.core.subject',
        string='Cours non soumis',
        compute='_compute_subjects_call'
    )

    number_of_subjects_not_submitted = fields.Integer(
        string='Nombre de cours non soumis',
        compute='_compute_subjects_call',
    )

    number_of_subjects_hour = fields.Float(
        string='Nombre d\'heures prévues',
        compute='_compute_subjects_call',
        store=True,
    )

    @api.depends('subject_ids')
    def _compute_subjects_call(self):
        for record in self:
            record._compute_number_of_subjects()
            record._compute_number_of_subjects_hour()
            record._compute_subjects_validated()
            record._compute_number_of_subjects_validated()
            record._compute_subjects_not_validated()
            record._compute_number_of_subjects_not_validated()
            record._compute_subjects_submitted()
            record._compute_number_of_subjects_submitted()
            record._compute_subjects_not_submitted()
            record._compute_number_of_subjects_not_submitted()

    @api.onchange('subject_ids')
    def _onchange_subjects_call(self):
        for record in self:
            record._compute_subjects_call()

    def _compute_number_of_subjects(self):
        for record in self:
            record.number_of_subjects = len(record.subject_ids.ids)

    def _compute_number_of_subjects_hour(self):
        for record in self:
            total = 0.0
            subject_ids = record.subject_ids
            for subject in subject_ids:
                total += subject.hours_credit

            total = round(total, 2)

            record.number_of_subjects_hour = total

    def _compute_subjects_validated(self):
        for record in self:
            timetables = self.env['siantou.ems.timetable.timetable'].search([
                ('class_id', '=', record.id),
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
                ('subject_id', 'in', record.subject_ids.ids),
            ])

            semester_user = self.env['ir.config_parameter'].sudo().get_param(f'siantou.semester_user_{self.env.user.id}', '')
            if semester_user:
                semester_user = int(semester_user)
                timetables = timetables.filtered(lambda rec: rec.semester_id.id == semester_user)

            timetables = list(timetables)
            timetable_subject_ids = [timetable.subject_id.id for timetable in timetables]
            timetable_subject_ids = list(set(timetable_subject_ids))
            subject_ids = record.subject_ids.filtered(lambda rec: rec.id in timetable_subject_ids)

            record.subjects_validated_ids = subject_ids

    def _compute_number_of_subjects_validated(self):
        for record in self:
            timetables = self.env['siantou.ems.timetable.timetable'].search([
                ('class_id', '=', record.id),
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
                ('subject_id', 'in', record.subject_ids.ids),
            ])

            semester_user = self.env['ir.config_parameter'].sudo().get_param(f'siantou.semester_user_{self.env.user.id}', '')
            if semester_user:
                semester_user = int(semester_user)
                timetables = timetables.filtered(lambda rec: rec.semester_id.id == semester_user)

            timetables = list(timetables)
            timetable_subject_ids = [timetable.subject_id.id for timetable in timetables]
            timetable_subject_ids = list(set(timetable_subject_ids))
            subject_ids = record.subject_ids.filtered(lambda rec: rec.id in timetable_subject_ids)

            record.number_of_subjects_validated = len(subject_ids.ids)

    def _compute_subjects_not_validated(self):
        for record in self:
            timetables = self.env['siantou.ems.timetable.timetable'].search([
                ('class_id', '=', record.id),
                '|',
                '&',
                '&',
                ('group_id.is_active', '=', True),
                ('group_id.is_submit', '=', False),
                ('group_id.status', '=', 'pending'),
                '&',
                '&',
                '&',
                ('group_parent_id.is_active', '=', True),
                ('group_parent_id.is_submit', '=', False),
                ('group_parent_id.status', '=', 'pending'),
                ('group_id.status', '=', 'pending'),
                ('is_active', '=', True),
                ('subject_id', 'in', record.subject_ids.ids),
            ])

            semester_user = self.env['ir.config_parameter'].sudo().get_param(f'siantou.semester_user_{self.env.user.id}', '')
            if semester_user:
                semester_user = int(semester_user)
                timetables = timetables.filtered(lambda rec: rec.semester_id.id == semester_user)

            timetables = list(timetables)
            timetable_subject_ids = [timetable.subject_id.id for timetable in timetables]
            timetable_subject_ids = list(set(timetable_subject_ids))
            subject_ids = record.subject_ids.filtered(lambda rec: rec.id in timetable_subject_ids)

            record.subjects_not_validated_ids = subject_ids

    def _compute_number_of_subjects_not_validated(self):
        for record in self:
            timetables = self.env['siantou.ems.timetable.timetable'].search([
                ('class_id', '=', record.id),
                '|',
                '&',
                '&',
                ('group_id.is_active', '=', True),
                ('group_id.is_submit', '=', False),
                ('group_id.status', '=', 'pending'),
                '&',
                '&',
                '&',
                ('group_parent_id.is_active', '=', True),
                ('group_parent_id.is_submit', '=', False),
                ('group_parent_id.status', '=', 'pending'),
                ('group_id.status', '=', 'pending'),
                ('is_active', '=', True),
                ('subject_id', 'in', record.subject_ids.ids),
            ])

            semester_user = self.env['ir.config_parameter'].sudo().get_param(f'siantou.semester_user_{self.env.user.id}', '')
            if semester_user:
                semester_user = int(semester_user)
                timetables = timetables.filtered(lambda rec: rec.semester_id.id == semester_user)

            timetables = list(timetables)
            timetable_subject_ids = [timetable.subject_id.id for timetable in timetables]
            timetable_subject_ids = list(set(timetable_subject_ids))
            subject_ids = record.subject_ids.filtered(lambda rec: rec.id in timetable_subject_ids)

            record.number_of_subjects_not_validated = len(subject_ids.ids)

    def _compute_subjects_submitted(self):
        for record in self:
            timetables = self.env['siantou.ems.timetable.timetable'].search([
                ('class_id', '=', record.id),
                '|',
                '&',
                '&',
                ('group_id.is_active', '=', True),
                ('group_id.is_submit', '=', False),
                ('group_id.status', 'in', ['valid', 'pending']),
                '&',
                '&',
                '&',
                ('group_parent_id.is_active', '=', True),
                ('group_parent_id.is_submit', '=', False),
                ('group_parent_id.status', 'in', ['valid', 'pending']),
                ('group_id.status', 'in', ['valid', 'pending']),
                ('is_active', '=', True),
                ('subject_id', 'in', record.subject_ids.ids),
            ])

            semester_user = self.env['ir.config_parameter'].sudo().get_param(f'siantou.semester_user_{self.env.user.id}', '')
            if semester_user:
                semester_user = int(semester_user)
                timetables = timetables.filtered(lambda rec: rec.semester_id.id == semester_user)

            timetables = list(timetables)
            timetable_subject_ids = [timetable.subject_id.id for timetable in timetables]
            timetable_subject_ids = list(set(timetable_subject_ids))
            subject_ids = record.subject_ids.filtered(lambda rec: rec.id in timetable_subject_ids)

            record.subjects_submitted_ids = subject_ids

    def _compute_number_of_subjects_submitted(self):
        for record in self:
            timetables = self.env['siantou.ems.timetable.timetable'].search([
                ('class_id', '=', record.id),
                '|',
                '&',
                '&',
                ('group_id.is_active', '=', True),
                ('group_id.is_submit', '=', False),
                ('group_id.status', 'in', ['valid', 'pending']),
                '&',
                '&',
                '&',
                ('group_parent_id.is_active', '=', True),
                ('group_parent_id.is_submit', '=', False),
                ('group_parent_id.status', 'in', ['valid', 'pending']),
                ('group_id.status', 'in', ['valid', 'pending']),
                ('is_active', '=', True),
                ('subject_id', 'in', record.subject_ids.ids),
            ])

            semester_user = self.env['ir.config_parameter'].sudo().get_param(f'siantou.semester_user_{self.env.user.id}', '')
            if semester_user:
                semester_user = int(semester_user)
                timetables = timetables.filtered(lambda rec: rec.semester_id.id == semester_user)

            timetables = list(timetables)
            timetable_subject_ids = [timetable.subject_id.id for timetable in timetables]
            timetable_subject_ids = list(set(timetable_subject_ids))
            subject_ids = record.subject_ids.filtered(lambda rec: rec.id in timetable_subject_ids)

            record.number_of_subjects_submitted = len(subject_ids.ids)

    def _compute_subjects_not_submitted(self):
        for record in self:
            timetables = self.env['siantou.ems.timetable.timetable'].search([
                ('class_id', '=', record.id),
                '|',
                '&',
                '&',
                ('group_id.is_active', '=', True),
                ('group_id.is_submit', '=', False),
                ('group_id.status', 'in', ['valid', 'pending']),
                '&',
                '&',
                '&',
                ('group_parent_id.is_active', '=', True),
                ('group_parent_id.is_submit', '=', False),
                ('group_parent_id.status', 'in', ['valid', 'pending']),
                ('group_id.status', 'in', ['valid', 'pending']),
                ('is_active', '=', True),
                ('subject_id', 'in', record.subject_ids.ids),
            ])

            semester_user = self.env['ir.config_parameter'].sudo().get_param(f'siantou.semester_user_{self.env.user.id}', '')
            if semester_user:
                semester_user = int(semester_user)
                timetables = timetables.filtered(lambda rec: rec.semester_id.id == semester_user)

            timetables = list(timetables)
            timetable_subject_ids = [timetable.subject_id.id for timetable in timetables]
            timetable_subject_ids = list(set(timetable_subject_ids))
            subject_ids = record.subject_ids.filtered(lambda rec: rec.id not in timetable_subject_ids)

            record.subjects_not_submitted_ids = subject_ids

    def _compute_number_of_subjects_not_submitted(self):
        for record in self:
            timetables = self.env['siantou.ems.timetable.timetable'].search([
                ('class_id', '=', record.id),
                '|',
                '&',
                '&',
                ('group_id.is_active', '=', True),
                ('group_id.is_submit', '=', False),
                ('group_id.status', 'in', ['valid', 'pending']),
                '&',
                '&',
                '&',
                ('group_parent_id.is_active', '=', True),
                ('group_parent_id.is_submit', '=', False),
                ('group_parent_id.status', 'in', ['valid', 'pending']),
                ('group_id.status', 'in', ['valid', 'pending']),
                ('is_active', '=', True),
                ('subject_id', 'in', record.subject_ids.ids),
            ])

            semester_user = self.env['ir.config_parameter'].sudo().get_param(f'siantou.semester_user_{self.env.user.id}', '')
            if semester_user:
                semester_user = int(semester_user)
                timetables = timetables.filtered(lambda rec: rec.semester_id.id == semester_user)

            timetables = list(timetables)
            timetable_subject_ids = [timetable.subject_id.id for timetable in timetables]
            timetable_subject_ids = list(set(timetable_subject_ids))
            subject_ids = record.subject_ids.filtered(lambda rec: rec.id not in timetable_subject_ids)

            record.number_of_subjects_not_submitted = len(subject_ids.ids)

    type_cour = fields.Selection([
            ('cj', 'Cours du jour'),
            ('cs', 'Cours du soir'),
        ], string='Type de cours',
        default='cj',
    )

    class_group_ids = fields.One2many(
        'siantou.ems.core.class.group',
        'class_id',
        string='Groupes de classe'
    )

    is_timetable_active = fields.Boolean(string='Emplois du temps actifs ?', default=False)

    timetable_inactive_date = fields.Date(
        string='Date de désactivation des emplois du temps',
        compute='_compute_timetable_inactive_date',
        store=True,
        readonly=False
    )

    @api.depends('is_timetable_active')
    def _compute_timetable_inactive_date(self):
        for record in self:
            if record.is_timetable_active:
                record.timetable_inactive_date = None
            else:
                record.timetable_inactive_date = date.today()

    @api.onchange('is_timetable_active')
    def _onchange_timetable_inactive_date(self):
        for record in self:
            if record.is_timetable_active:
                record.timetable_inactive_date = None
            else:
                record.timetable_inactive_date = date.today()

    @api.constrains('is_timetable_active', 'timetable_inactive_date')
    def _check_inactive_date(self):
        for record in self:
            if not record.is_timetable_active:
                if not record.timetable_inactive_date:
                    raise ValidationError(f"La désactivation des emplois du temps doit avoir une date de désactivation")

    # _sql_constraints = [
    #     ('unique_year_specialty_option_level_type_cour', 'unique(year_id,specialty_id,option_id,level_id,type_cour)', 'L\'année académique, la spécialité, l\'option, le niveau, et le type de cours doivent être uniques.'),
    # ]

    @api.constrains('year_id', 'specialty_id', 'option_id', 'level_id', 'type_cour')
    def _check_unique_year_specialty_option_level_type_cour(self):
        for record in self:
            if record.option_id.id:
                classes = self.env['siantou.ems.core.class'].search([
                    ('id', '!=', record.id),
                    ('year_id', '=', record.year_id.id),
                    ('specialty_id', '=', record.specialty_id.id),
                    ('option_id', '=', record.option_id.id),
                    ('level_id', '=', record.level_id.id),
                    ('type_cour', '=', record.type_cour),
                ])
            else:
                classes = self.env['siantou.ems.core.class'].search([
                    ('id', '!=', record.id),
                    ('year_id', '=', record.year_id.id),
                    ('specialty_id', '=', record.specialty_id.id),
                    ('option_id', '=', False),
                    ('level_id', '=', record.level_id.id),
                    ('type_cour', '=', record.type_cour),
                ])
            classes = list(classes)
            if len(classes) > 0:
                validation_error_message = """
                    Deux classes de même année académique, spécialité, option, niveau, et type de cours ne peuvent être crées
                    -----
                """
                for classe in classes:
                    validation_error_message += f"""
                        • ID : {classe.id}
                        Classe : {classe.name}
                        Année académique : {classe.year_id.name}
                        Spécialité : {classe.specialty_id.name}
                        Option : {classe.option_id.name}
                        Niveau : {classe.level_id.name}
                        Type de cours : {TYPE_COUR[classe.type_cour]}
                        -----
                    """
                raise ValidationError(validation_error_message)

    @api.depends('specialty_id', 'option_id', 'level_id', 'type_cour', 'supervision_id')
    def _compute_name(self):
        for record in self:
            specialty_name = record.specialty_id.name if record.specialty_id.id else ''
            specialty_name = specialty_name.lower()
            while True:
                if specialty_name.find('-') != -1:
                    specialty_name = specialty_name.replace('-', ' ')
                else:
                    break
            option_name = record.option_id.name if record.option_id.id else ''
            option_name = option_name.lower()
            while True:
                if option_name.find('-') != -1:
                    option_name = option_name.replace('-', ' ')
                else:
                    break
            if option_name != '':
                option_name = f'- {option_name}'
            niveau_name = record.level_id.name if record.level_id.id else ''
            niveau_name = re.sub(r'Niveau ', '', niveau_name)
            type_cour_name = record.type_cour if record.type_cour == 'cs' else ''
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
            name = '{} {} {} {} {}'.format(specialty_name, option_name, niveau_name, type_cour_name, supervision_name)
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

    @api.onchange('specialty_id', 'option_id', 'level_id', 'type_cour', 'supervision_id')
    def _onchange_name(self):
        for record in self:
            record._compute_name()

    @api.depends('student_enroll_ids')
    def _compute_students_call(self):
        for record in self:
            record._compute_students()
            record._compute_number_of_students()

    @api.onchange('student_enroll_ids')
    def _onchange_students_call(self):
        for record in self:
            record._compute_students_call()

    def _compute_students(self):
        for record in self:
            students = []
            for student_enroll_id in record.student_enroll_ids:
                if student_enroll_id.is_active_candidature == True and student_enroll_id.status == "transfer":
                    students.append(student_enroll_id.student_id.id)

            student_ids = self.env['oe.school.student'].search([
                ('id', 'in', students),
            ])

            record.student_ids = student_ids

    def _compute_number_of_students(self):
        for record in self:
            students = []
            for student_enroll_id in record.student_enroll_ids:
                if student_enroll_id.is_active_candidature == True and student_enroll_id.status == "transfer":
                    students.append(student_enroll_id.student_id.id)

            student_ids = self.env['oe.school.student'].search([
                ('id', 'in', students),
            ])

            record.number_of_student = len(student_ids.ids)

    @api.depends('timetable_ids')
    def _compute_hours_call(self):
        for record in self:
            record._compute_number_of_hours()
            record._compute_number_of_worked_hours()

    @api.onchange('timetable_ids')
    def _onchange_hours_call(self):
        for record in self:
            record._compute_hours_call()

    def _compute_number_of_hours(self):
        for record in self:
            total = 0.0
            key_timetables = {}
            for timetable in record.timetable_ids:
                if not timetable.date or not timetable.day_of_week or not timetable.employee_id.id:
                    continue

                end_time = EducationClass.convert_float_to_time(timetable.end_time, has_second=True)
                start_time = EducationClass.convert_float_to_time(timetable.start_time, has_second=True)
                key = '{}-{}-{}'.format(timetable.date, start_time, end_time)
                if key not in key_timetables:
                    key_timetables[key] = {}
                    key_timetables[key]['timetable'] = timetable
                else:
                    continue

                end_time = EducationClass.convert_float_to_time(timetable.end_time, has_second=True)
                start_time = EducationClass.convert_float_to_time(timetable.start_time, has_second=True)
                end_time = datetime.strptime(f"{timetable.date} {end_time}", DATETIME_FORMAT)
                start_time = datetime.strptime(f"{timetable.date} {start_time}", DATETIME_FORMAT)

                worked_hours = end_time - start_time
                worked_hours = worked_hours.total_seconds() / 3600.0
                worked_hours = round(worked_hours, 2)

                if worked_hours < 0.0:
                    del(key_timetables[key])
                    continue

                total += worked_hours

            total = round(total, 2)

            record.number_of_hours = total

    def _compute_number_of_worked_hours(self):
        for record in self:
            total = 0.0
            key_timetables = {}
            timetable_ids = record.timetable_ids.filtered(lambda rec: rec.status in ['present', 'permission'])
            timetable_ids = list(timetable_ids)
            for timetable in timetable_ids:
                if not timetable.date or not timetable.day_of_week or not timetable.employee_id.id:
                    continue

                end_time = EducationClass.convert_float_to_time(timetable.end_time, has_second=True)
                start_time = EducationClass.convert_float_to_time(timetable.start_time, has_second=True)
                key = '{}-{}-{}'.format(timetable.date, start_time, end_time)
                if key not in key_timetables:
                    key_timetables[key] = {}
                    key_timetables[key]['timetable'] = timetable
                else:
                    continue

                end_time = EducationClass.convert_float_to_time(timetable.end_time, has_second=True)
                start_time = EducationClass.convert_float_to_time(timetable.start_time, has_second=True)
                end_time = datetime.strptime(f"{timetable.date} {end_time}", DATETIME_FORMAT)
                start_time = datetime.strptime(f"{timetable.date} {start_time}", DATETIME_FORMAT)

                worked_hours = end_time - start_time
                worked_hours = worked_hours.total_seconds() / 3600.0
                worked_hours = round(worked_hours, 2)

                if worked_hours < 0.0:
                    del(key_timetables[key])
                    continue

                total += worked_hours

            total = round(total, 2)

            record.number_of_worked_hours = total

    @api.depends('ue_ids')
    def _compute_subjects(self):
        for record in self:
            ue_ids = record.ue_ids
            semester_user = self.env['ir.config_parameter'].sudo().get_param(f'siantou.semester_user_{self.env.user.id}', '')
            if semester_user:
                semester_user = int(semester_user)
                ue_ids = ue_ids.filtered(lambda rec: semester_user in rec.semester_ids.ids)

            subject_ids = self.env['siantou.ems.core.subject'].search([
                ('ue_ids', 'in', ue_ids.ids)
            ])

            record.subject_ids = subject_ids

    @api.onchange('ue_ids')
    def _onchange_subjects(self):
        for record in self:
            record._compute_subjects()

    @api.onchange('school_id')
    def _onchange_school(self):
        for record in self:
            record.field_of_study_id = None
            record.specialty_id = None
            record.option_id = None

    @api.onchange('field_of_study_id')
    def _onchange_filiere(self):
        for record in self:
            record.specialty_id = None
            record.option_id = None

    @api.onchange('specialty_id')
    def _onchange_specialty(self):
        for record in self:
            record.option_id = None

    def get_subjects_validated(self):
        domain = [
            ('id', 'in', self.subjects_validated_ids.ids),
        ]

        return {
            'name': 'Cours validés',
            'type': 'ir.actions.act_window',
            'res_model': 'siantou.ems.core.subject',
            'view_mode': 'tree',
            'domain': domain,
            'context': {
                'create': False,
                'edit': False,
            },
            'target': 'main',
        }

    def get_subjects_not_validated(self):
        domain = [
            ('id', 'in', self.subjects_not_validated_ids.ids),
        ]

        return {
            'name': 'Cours non validés',
            'type': 'ir.actions.act_window',
            'res_model': 'siantou.ems.core.subject',
            'view_mode': 'tree',
            'domain': domain,
            'context': {
                'create': False,
                'edit': False,
            },
            'target': 'main',
        }

    def get_subjects(self):
        domain = [
            ('id', 'in', self.subject_ids.ids),
        ]

        return {
            'name': 'Cours',
            'type': 'ir.actions.act_window',
            'res_model': 'siantou.ems.core.subject',
            'view_mode': 'tree',
            'domain': domain,
            'context': {
                'create': False,
                'edit': False,
            },
            'target': 'main',
        }

    def get_subjects_submitted(self):
        domain = [
            ('id', 'in', self.subjects_submitted_ids.ids),
        ]

        return {
            'name': 'Cours soumis',
            'type': 'ir.actions.act_window',
            'res_model': 'siantou.ems.core.subject',
            'view_mode': 'tree',
            'domain': domain,
            'context': {
                'create': False,
                'edit': False,
            },
            'target': 'main',
        }

    def get_subjects_not_submitted(self):
        domain = [
            ('id', 'in', self.subjects_not_submitted_ids.ids),
        ]

        return {
            'name': 'Cours non soumis',
            'type': 'ir.actions.act_window',
            'res_model': 'siantou.ems.core.subject',
            'view_mode': 'tree',
            'domain': domain,
            'context': {
                'create': False,
                'edit': False,
            },
            'target': 'main',
        }

    @api.depends('year_id', 'specialty_id', 'option_id', 'level_id', 'type_cour')
    def _compute_timetables(self):
        # Recherche des emplois du temps qui correspondent à la spécialité et au niveau
        for record in self:
            timetables = self.env['siantou.ems.timetable.timetable'].search([
                ('class_id', '=', record.id),
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
            ])

            # Affecter les emplois du temps trouvés à l'attribut timetable_ids
            record.timetable_ids = timetables

    @api.onchange('year_id', 'specialty_id', 'option_id', 'level_id', 'type_cour')
    def _onchange_timetables(self):
        for record in self:
            record._compute_timetables()

    def write(self, vals):
        classes = []
        if len(self.ids) == 1:
            classe = self.env['siantou.ems.core.class'].browse(self.id)
            classes.append(classe)
        else:
            classes = self.env['siantou.ems.core.class'].browse(self.ids)
            classes = list(classes)

        res = super(EducationClass, self).write(vals)

        if 'is_timetable_active' in vals:
            for classe in classes:
                timetables = self.env['siantou.ems.timetable.timetable'].search([
                    ('class_id', '=', classe.id),
                    '|',
                    ('group_id.is_submit', '=', False),
                    ('group_parent_id.is_submit', '=', False),
                ])
                timetables = list(timetables)
                for timetable in timetables:
                    timetable.write({
                        'class_id': classe.id,
                        'skip_validation': True,
                        'worked_start_time': 0.0,
                        'worked_end_time': 0.0,
                        'worked_time': 0.0,
                        'rate': 0.0,
                        'amount': 0.0,
                        'status': 'pending',
                        'reason': None,
                    })

        if 'name' in vals and vals['name'] and vals['name'].strip():
            for classe in classes:
                timetables = self.env['siantou.ems.timetable.timetable'].search([
                    ('class_id', '=', classe.id),
                    '|',
                    ('group_id.is_submit', '=', False),
                    ('group_parent_id.is_submit', '=', False),
                ])
                timetables = list(timetables)
                for timetable in timetables:
                    timetable.write({
                        'class_id': classe.id,
                        'skip_validation': True,
                    })

        return res

    def action_open_filter(self):
        view_id = self.env.ref('siantou_ems_core.class_filter_wizard').id
        return {
            'name': 'Filtre des classes',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'class.filter.wizard',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': {
                'default_year_id': self.env['siantou.ems.core.year'].search([('is_active', '=', True)], limit=1).id,
                'default_status': None,
            },
        }

    def action_open_filter_kanban(self):
        view_id = self.env.ref('siantou_ems_core.class_filter_wizard').id
        return {
            'name': 'Filtre des classes',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'class.filter.wizard',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': {
                'default_year_id': self.env['siantou.ems.core.year'].search([('is_active', '=', True)], limit=1).id,
                'default_status': None,
                'default_type_action': 'kanban',
            },
        }

    def action_reset_filter(self):
        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', '')
        self.env['ir.config_parameter'].sudo().set_param(f'siantou.semester_user_{self.env.user.id}', '')
        action = self.env.ref('siantou_ems_core.action_show_class').read()[0]
        action.update({
            'target': 'main',
        })
        return action

    def action_reset_filter_kanban(self):
        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', '')
        self.env['ir.config_parameter'].sudo().set_param(f'siantou.semester_user_{self.env.user.id}', '')
        action = self.env.ref('siantou_ems_core.action_show_class_dashboard').read()[0]
        action.update({
            'target': 'main',
        })
        return action

    def action_print_pdf(self):
        active_ids = self.env.context.get('active_ids', [])
        classes = self.env['siantou.ems.core.class'].browse(active_ids)
        classes = list(classes)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')
        report_data = self.env['class.print.wizard'].create({})
        domains = [
            ('id', 'in', active_ids)
        ]
        data = report_data.print_class_report_data(domains=domains)

        schools = self.env['siantou.ems.core.school'].search([])
        for school in schools:
            if data['docdata']['filter'].find(school.name) != -1:
                data['docdata']['title'] = '{} {}'.format(data['docdata']['title'], school.name)
                break
        levels = self.env['siantou.ems.core.level'].search([])
        for level in levels:
            if data['docdata']['filter'].find(level.name) != -1:
                data['docdata']['title'] = '{} {}'.format(data['docdata']['title'], level.name)
                break

        if len(data['docdata']['class_data']) == 0:
            raise UserError('Aucune donnée trouvée')
        report_action = self.env.ref('siantou_ems_core.action_report_class')
        report_action.update({
            'name': '{} PDF'.format(data['docdata']['title']),
        })
        return report_action.report_action(self, data=data)

    def action_print_kanban_pdf(self):
        domain = self.env.context.get('active_domain', [])
        classes = self.env['siantou.ems.core.class'].search(domain)
        classes = list(classes)
        active_ids = []
        for classe in classes:
            active_ids.append(classe.id)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée filtrée')
        report_data = self.env['class.print.wizard'].create({})
        domains = [
            ('id', 'in', active_ids)
        ]
        data = report_data.print_class_report_data(domains=domains)

        schools = self.env['siantou.ems.core.school'].search([])
        for school in schools:
            if data['docdata']['filter'].find(school.name) != -1:
                data['docdata']['title'] = '{} {}'.format(data['docdata']['title'], school.name)
                break
        levels = self.env['siantou.ems.core.level'].search([])
        for level in levels:
            if data['docdata']['filter'].find(level.name) != -1:
                data['docdata']['title'] = '{} {}'.format(data['docdata']['title'], level.name)
                break

        if len(data['docdata']['class_data']) == 0:
            raise UserError('Aucune donnée trouvée')
        report_action = self.env.ref('siantou_ems_core.action_report_class')
        report_action.update({
            'name': '{} PDF'.format(data['docdata']['title']),
        })
        return report_action.report_action(self, data=data)

    def add_number_of_student_class(self, classe):
        try:
            classe._compute_students_call()
            classe.sudo().write({
                'specialty_id': classe.specialty_id.id,
            })
            # self.env.cr.commit()
        except psycopg2.errors.NotNullViolation as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except psycopg2.Error as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except Exception as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

    def sort_ue_class(self, classe):
        n = len(classe.ue_ids.ids)
        return n

    def sort_student_class(self, classe):
        n = len(classe.student_ids.ids)
        return n

    def remove_duplicate_student_class(self, classes):
        try:
            exist_classes = {}
            for classe in classes:
                if classe.name not in exist_classes:
                    exist_classes[classe.name] = []
                    exist_classes[classe.name].append(classe)
                else:
                    exist_classes[classe.name].append(classe)

            for k in exist_classes.keys():
                ue_classes = [classe for classe in exist_classes[k] if len(classe.ue_ids.ids) > 0]
                ue_classes = sorted(ue_classes, key=self.sort_ue_class, reverse=True)
                student_classes = [classe for classe in exist_classes[k] if len(classe.ue_ids.ids) == 0]
                student_classes = sorted(student_classes, key=self.sort_student_class, reverse=True)
                exist_classes[k] = ue_classes + student_classes
                if len(exist_classes[k]) > 0:
                    exist_classe = None
                    for i, classe in enumerate(exist_classes[k]):
                        if i == 0:
                            exist_classe = classe
                        else:
                            for student_id in classe.student_ids:
                                student_id.write({
                                    'class_id': exist_classe.id,
                                    'specialty_id': exist_classe.specialty_id.id,
                                    'field_of_study_id': exist_classe.specialty_id.field_of_study_id.id,
                                    'cycle_id': exist_classe.specialty_id.field_of_study_id.cycle_id.id,
                                    'school_id': exist_classe.specialty_id.field_of_study_id.school_id.id,
                                })
                            for student_enroll_id in classe.student_enroll_ids:
                                student_enroll_id.write({
                                    'class_id': exist_classe.id,
                                    'specialty_id': exist_classe.specialty_id.id,
                                    'field_of_study_id': exist_classe.specialty_id.field_of_study_id.id,
                                    'cycle_id': exist_classe.specialty_id.field_of_study_id.cycle_id.id,
                                    'school_id': exist_classe.specialty_id.field_of_study_id.school_id.id,
                                })
                            classe.unlink()
            # self.env.cr.commit()
        except psycopg2.errors.NotNullViolation as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except psycopg2.Error as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except Exception as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

    def update_class(self, classe):
        try:
            classe.write({
                'specialty_id': classe.specialty_id.id,
            })
            # self.env.cr.commit()
        except psycopg2.errors.NotNullViolation as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except psycopg2.Error as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except Exception as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

    def action_update_all_student_class(self):
        active_ids = self.env.context.get('active_ids', [])
        classes = self.env['siantou.ems.core.class'].browse(active_ids)
        classes = list(classes)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')

        for classe in classes:
            self.add_number_of_student_class(classe)

        self.remove_duplicate_student_class(classes)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_update_all_class(self):
        active_ids = self.env.context.get('active_ids', [])
        classes = self.env['siantou.ems.core.class'].browse(active_ids)
        classes = list(classes)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')

        for classe in classes:
            self.update_class(classe)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def update_group_class(self, classe):
        try:
            groups = []
            class_group_ids = self.env['siantou.ems.core.class.group'].search([('class_id', '!=', False)])
            class_group_ids = list(class_group_ids)
            for class_group_id in class_group_ids:
                name = class_group_id.name
                name = name.strip()
                name = name.lower()
                groups.append(name)

            groups = list(set(groups))

            for group in groups:
                class_group = None
                class_group_ids = classe.class_group_ids.filtered(lambda rec: rec.name.strip().lower() == group)
                class_group_ids = list(class_group_ids)
                for i, class_group_id in enumerate(class_group_ids):
                    if i == 0:
                        class_group = class_group_id
                    else:
                        timetable_ids = self.env['siantou.ems.timetable.timetable'].search([
                            ('class_id', '=', classe.id),
                            ('class_group_id', '=', class_group_id.id)
                        ])
                        timetable_ids = list(timetable_ids)
                        for timetable_id in timetable_ids:
                            timetable_id.write({
                                'class_group_id': class_group.id,
                                'skip_validation': True,
                            })
                        class_group_id.unlink()
            # self.env.cr.commit()
        except psycopg2.errors.NotNullViolation as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except psycopg2.Error as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except Exception as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

    def action_update_all_group_class(self):
        active_ids = self.env.context.get('active_ids', [])
        classes = self.env['siantou.ems.core.class'].browse(active_ids)
        classes = list(classes)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')

        for classe in classes:
            self.update_group_class(classe)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_update_dashboard_class(self):
        active_ids = self.env.context.get('active_ids', [])
        classes = self.env['siantou.ems.core.class'].browse(active_ids)
        classes = list(classes)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')

        for classe in classes:
            classe._compute_students_call()
            classe._compute_timetables()
            classe._compute_hours_call()
            classe._compute_subjects()
            classe._compute_subjects_call()
            classe._compute_hours_credit_call()
            classe.sudo().write({
                'specialty_id': classe.specialty_id.id,
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_open_copy(self):
        view_id = self.env.ref('siantou_ems_core.class_copy_wizard_form').id
        return {
            'name': 'Copie des classes',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'class.copy.wizard',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': {
                'default_source_year_id': self.env['siantou.ems.core.year'].search([('is_active', '=', True)], limit=1).id,
            },
        }

    def action_print_class_subject_pdf(self):
        active_ids = self.env.context.get('active_ids', [])
        classes = self.env['siantou.ems.core.class'].browse(active_ids)
        classes = list(classes)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')
        report_data = self.env['class.print.wizard'].create({})
        domains = [
            ('id', 'in', active_ids)
        ]
        data = report_data.print_class_subject_report_data(domains=domains)

        schools = self.env['siantou.ems.core.school'].search([])
        for school in schools:
            if data['docdata']['filter'].find(school.name) != -1:
                data['docdata']['title'] = '{} {}'.format(data['docdata']['title'], school.name)
                break
        levels = self.env['siantou.ems.core.level'].search([])
        for level in levels:
            if data['docdata']['filter'].find(level.name) != -1:
                data['docdata']['title'] = '{} {}'.format(data['docdata']['title'], level.name)
                break

        if len(data['docdata']['subject_data']) == 0:
            raise UserError('Aucune donnée trouvée')

        subjects = {}

        for d in data['docdata']['subject_data']:
            key_class = '{}'.format(d['class_id'])
            key_semester = '{}'.format(d['semester_id'])
            key_ue = '{}'.format(d['ue_id'])
            if key_class not in subjects:
                subjects[key_class] = {}
                subjects[key_class]['id'] = d['class_id']
                subjects[key_class]['name'] = d['class_name']
                subjects[key_class]['data'] = {}
                subjects[key_class]['data'][key_semester] = {}
                subjects[key_class]['data'][key_semester]['name'] = d['semester_name']
                subjects[key_class]['data'][key_semester]['data'] = {}
                subjects[key_class]['data'][key_semester]['data'][key_ue] = {}
                subjects[key_class]['data'][key_semester]['data'][key_ue]['code'] = d['ue_code']
                subjects[key_class]['data'][key_semester]['data'][key_ue]['name'] = d['ue_name']
                subjects[key_class]['data'][key_semester]['data'][key_ue]['data'] = []
                subjects[key_class]['data'][key_semester]['data'][key_ue]['data'].append(d)
            else:
                if key_semester not in subjects[key_class]['data']:
                    subjects[key_class]['data'][key_semester] = {}
                    subjects[key_class]['data'][key_semester]['name'] = d['semester_name']
                    subjects[key_class]['data'][key_semester]['data'] = {}
                    subjects[key_class]['data'][key_semester]['data'][key_ue] = {}
                    subjects[key_class]['data'][key_semester]['data'][key_ue]['code'] = d['ue_code']
                    subjects[key_class]['data'][key_semester]['data'][key_ue]['name'] = d['ue_name']
                    subjects[key_class]['data'][key_semester]['data'][key_ue]['data'] = []
                    subjects[key_class]['data'][key_semester]['data'][key_ue]['data'].append(d)
                else:
                    if key_ue not in subjects[key_class]['data'][key_semester]['data']:
                        subjects[key_class]['data'][key_semester]['data'][key_ue] = {}
                        subjects[key_class]['data'][key_semester]['data'][key_ue]['code'] = d['ue_code']
                        subjects[key_class]['data'][key_semester]['data'][key_ue]['name'] = d['ue_name']
                        subjects[key_class]['data'][key_semester]['data'][key_ue]['data'] = []
                        subjects[key_class]['data'][key_semester]['data'][key_ue]['data'].append(d)
                    else:
                        subjects[key_class]['data'][key_semester]['data'][key_ue]['data'].append(d)

        _logger.info(f'----------- tototototototo subjects {subjects} -----------')

        data['docdata']['subject_data'] = subjects

        data['docdata']['subject_data'] = dict(sorted(data['docdata']['subject_data'].items(), key=lambda item: item[1]['name'] if item[1]['name'] else ''))

        for key_class in data['docdata']['subject_data'].keys():
            data['docdata']['subject_data'][key_class]['hours_credit'] = 0.0
            data['docdata']['subject_data'][key_class]['total_credit'] = 0.0
            data['docdata']['subject_data'][key_class]['data'] = dict(sorted(data['docdata']['subject_data'][key_class]['data'].items(), key=lambda item: item[1]['name'] if item[1]['name'] else ''))
            for key_semester in data['docdata']['subject_data'][key_class]['data'].keys():
                data['docdata']['subject_data'][key_class]['data'][key_semester]['hours_credit'] = 0.0
                data['docdata']['subject_data'][key_class]['data'][key_semester]['total_credit'] = 0.0
                for key_ue in data['docdata']['subject_data'][key_class]['data'][key_semester]['data'].keys():
                    for subject in data['docdata']['subject_data'][key_class]['data'][key_semester]['data'][key_ue]['data']:
                        data['docdata']['subject_data'][key_class]['hours_credit'] += subject['hours_credit']
                        data['docdata']['subject_data'][key_class]['total_credit'] += subject['total_credit']
                        data['docdata']['subject_data'][key_class]['data'][key_semester]['hours_credit'] += subject['hours_credit']
                        data['docdata']['subject_data'][key_class]['data'][key_semester]['total_credit'] += subject['total_credit']

        for key_class in data['docdata']['subject_data'].keys():
            data['docdata']['subject_data'][key_class]['hours_credit'] = round(data['docdata']['subject_data'][key_class]['hours_credit'], 2)
            data['docdata']['subject_data'][key_class]['total_credit'] = round(data['docdata']['subject_data'][key_class]['total_credit'], 2)
            for key_semester in data['docdata']['subject_data'][key_class]['data'].keys():
                data['docdata']['subject_data'][key_class]['data'][key_semester]['hours_credit'] = round(data['docdata']['subject_data'][key_class]['data'][key_semester]['hours_credit'], 2)
                data['docdata']['subject_data'][key_class]['data'][key_semester]['total_credit'] = round(data['docdata']['subject_data'][key_class]['data'][key_semester]['total_credit'], 2)

        report_action = self.env.ref('siantou_ems_core.action_report_class_subject')
        report_action.update({
            'name': '{} PDF'.format(data['docdata']['title']),
        })
        return report_action.report_action(self, data=data)


class EducationClassGroup(models.Model):
    _name = 'siantou.ems.core.class.group'
    _description = 'Groupe de classe'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    name = fields.Char(string='Nom', required=True,
                       help="Entrer le nom du groupe")

    class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe',
        ondelete='cascade'
    )
