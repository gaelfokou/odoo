# -*- coding: utf-8 -*-

import re
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import unique
import logging

_logger = logging.getLogger(__name__)

class EducationClass(models.Model):
    _name = 'siantou.ems.core.class'
    _description = 'Classe'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    name = fields.Char(string='Nom',
                       compute='_compute_name', store=True,
                       help="Entrer le nom de la Classe")

    field_of_study_id = fields.Many2one('siantou.ems.core.field_of_study', string='Filière',
                                 required=True, help="Filière")

    cycle_id = fields.Many2one(
        'oe.school.course',
        string='Cursus ou Cycle',
        related='field_of_study_id.cycle_id',
        store=True
    )

    supervision_id = fields.Many2one('oe.school.course.supervision', string='Tutelle académique',
                                 help="Tutelle académique")

    student_enroll_ids = fields.One2many(
        'oe.school.student.enrollment',
        'class_id',
        string='Étudiants inscrits',
    )

    student_ids = fields.One2many(
        'oe.school.student',
        string='Étudiants',
        compute='_compute_students',
        store=False
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
        compute='_compute_number_of_student', store=True,
    )

    timetable_ids = fields.One2many(
        'siantou.ems.timetable.timetable',
        string='Emplois du temps',
        compute='_compute_timetables',
        store=False
    )

    specialty_id = fields.Many2one('siantou.ems.core.specialty', string='Spécialité',
                                 required=True, help="Spécialité")

    option_id = fields.Many2one('siantou.ems.core.option', string='Option',
                                 help="Option")

    level_id = fields.Many2one('siantou.ems.core.level', string='Niveau',
                                 required=True, help="Niveau")

    school_id = fields.Many2one('siantou.ems.core.school', string='École', required=True)

    year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année Académique',
        required=True,
        default=lambda self: self.env['siantou.ems.core.year'].search([('is_active', '=', True)], limit=1)
    )

    ue_ids = fields.Many2many('siantou.ems.core.unite.enseignement', 'class_ue_rel', 'class_id', 'ue_id', string='Unités d\'enseignement')

    group_ids = fields.Many2many('siantou.ems.timetable.group', 'class_group_rel', 'class_id', 'group_id', string='Versions d\'emploi du temps')

    subject_ids = fields.One2many(
        'siantou.ems.core.subject',
        string='Cours',
        compute='_compute_subjects',
        store=False
    )

    type_cour = fields.Selection([
            ('cj', 'Cours du jour'),
            ('cs', 'Cours du soir'),
        ],
        string='Type de cours',
        default='cj',
    )

    group_ids = fields.One2many(
        'siantou.ems.core.class.group',
        'class_id',
        string='Groupes de classe'
    )

    # _sql_constraints = [
    #     ('unique_year_specialty_option_level_type_cour', 'unique(year_id,specialty_id,option_id,level_id,type_cour)', 'L\'année académique, la spécialité, l\'option, le niveau, et le type de cours doivent être uniques.'),
    # ]

    @api.constrains('year_id', 'specialty_id', 'option_id', 'level_id', 'type_cour')
    def _check_unique_year_specialty_option_level_type_cour(self):
        for record in self:
            classes = self.env['siantou.ems.core.class'].search([
                ('id', '!=', record.id),
                ('year_id', '=', record.year_id.id),
                ('specialty_id', '=', record.specialty_id.id),
                ('option_id', '=', record.option_id.id),
                ('level_id', '=', record.level_id.id),
                ('type_cour', '=', record.type_cour),
            ])
            classes = list(classes)
            if len(classes) > 0:
                raise ValidationError(f"Deux classes de même année académique, spécialité, option, niveau, et type de cours ne peuvent être crées")

    @api.depends('specialty_id', 'option_id', 'level_id', 'type_cour')
    def _compute_name(self):
        for record in self:
            specialty_name = record.specialty_id.name if record.specialty_id.id else ''
            option_name = record.option_id.name if record.option_id.id else ''
            if option_name != '':
                option_name = f'- {option_name}'
            niveau_name = record.level_id.name if record.level_id.id else ''
            niveau_name = re.sub(r'Niveau ', '', niveau_name)
            type_cour_name = record.type_cour if record.type_cour == 'cs' else ''
            name = '{} {} {} {}'.format(specialty_name, option_name, niveau_name, type_cour_name)
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

    @api.onchange('specialty_id', 'option_id', 'level_id', 'type_cour')
    def _onchange_name(self):
        for record in self:
            specialty_name = record.specialty_id.name if record.specialty_id.id else ''
            option_name = record.option_id.name if record.option_id.id else ''
            if option_name != '':
                option_name = f'- {option_name}'
            niveau_name = record.level_id.name if record.level_id.id else ''
            niveau_name = re.sub(r'Niveau ', '', niveau_name)
            type_cour_name = record.type_cour if record.type_cour == 'cs' else ''
            name = '{} {} {} {}'.format(specialty_name, option_name, niveau_name, type_cour_name)
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

    @api.depends('student_enroll_ids')
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

    @api.onchange('student_enroll_ids')
    def _onchange_students(self):
        for record in self:
            students = []
            for student_enroll_id in record.student_enroll_ids:
                if student_enroll_id.is_active_candidature == True and student_enroll_id.status == "transfer":
                    students.append(student_enroll_id.student_id.id)

            student_ids = self.env['oe.school.student'].search([
                ('id', 'in', students),
            ])

            record.student_ids = student_ids

    @api.depends('student_enroll_ids')
    def _compute_number_of_student(self):
        for record in self:
            students = []
            for student_enroll_id in record.student_enroll_ids:
                if student_enroll_id.is_active_candidature == True and student_enroll_id.status == "transfer":
                    students.append(student_enroll_id.student_id.id)

            student_ids = self.env['oe.school.student'].search([
                ('id', 'in', students),
            ])

            record.number_of_student = len(student_ids.ids)

    @api.onchange('student_enroll_ids')
    def _onchange_student(self):
        for record in self:
            students = []
            for student_enroll_id in record.student_enroll_ids:
                if student_enroll_id.is_active_candidature == True and student_enroll_id.status == "transfer":
                    students.append(student_enroll_id.student_id.id)

            student_ids = self.env['oe.school.student'].search([
                ('id', 'in', students),
            ])

            record.number_of_student = len(student_ids.ids)

    @api.depends('ue_ids')
    def _compute_subjects(self):
        for record in self:
            subject_ids = self.env['siantou.ems.core.subject'].search([
                ('ue_ids', 'in', record.ue_ids.ids)
            ])

            record.subject_ids = subject_ids

    @api.onchange('ue_ids')
    def _onchange_subjects(self):
        for record in self:
            subject_ids = self.env['siantou.ems.core.subject'].search([
                ('ue_ids', 'in', record.ue_ids.ids)
            ])

            record.subject_ids = subject_ids

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

    @api.depends('year_id', 'specialty_id', 'option_id', 'level_id', 'type_cour')
    def _compute_timetables(self):
        # Recherche des emplois du temps qui correspondent à la spécialité et au niveau
        for record in self:
            timetables = []
            class_id = self.env['siantou.ems.core.class'].search([
                ('year_id', '=', record.year_id.id),
                ('specialty_id', '=', record.specialty_id.id),
                ('option_id', '=', record.option_id.id),
                ('level_id', '=', record.level_id.id),
                ('type_cour', '=', record.type_cour),
            ], limit=1)
            if class_id:
                timetables = self.env['siantou.ems.timetable.timetable'].search([
                    ('class_id', '=', class_id.id),
                    '|',
                    '&',
                    ('group_id.is_active', '=', True),
                    ('group_id.is_submit', '=', False),
                    '&',
                    ('group_parent_id.is_active', '=', True),
                    ('group_parent_id.is_submit', '=', False),
                ])

            # Affecter les emplois du temps trouvés à l'attribut timetable_ids
            record.timetable_ids = timetables

    @api.onchange('year_id', 'specialty_id', 'option_id', 'level_id', 'type_cour')
    def _onchange_timetables(self):
        # Recherche des emplois du temps qui correspondent à la spécialité et au niveau
        for record in self:
            timetables = []
            class_id = self.env['siantou.ems.core.class'].search([
                ('year_id', '=', record.year_id.id),
                ('specialty_id', '=', record.specialty_id.id),
                ('option_id', '=', record.option_id.id),
                ('level_id', '=', record.level_id.id),
                ('type_cour', '=', record.type_cour),
            ], limit=1)
            if class_id:
                timetables = self.env['siantou.ems.timetable.timetable'].search([
                    ('class_id', '=', class_id.id),
                    '|',
                    '&',
                    ('group_id.is_active', '=', True),
                    ('group_id.is_submit', '=', False),
                    '&',
                    ('group_parent_id.is_active', '=', True),
                    ('group_parent_id.is_submit', '=', False),
                ])

            # Affecter les emplois du temps trouvés à l'attribut timetable_ids
            record.timetable_ids = timetables

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

    def action_reset_filter(self):
        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', '')
        action = self.env.ref('siantou_ems_core.action_show_class').read()[0]
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

        # Appeler le rapport PDF
        if len(data['docdata']['class_data']) == 0:
            raise UserError('Aucune donnée trouvée')
        report_action = self.env.ref('siantou_ems_core.action_report_class')
        return report_action.report_action(self, data=data)

    def add_number_of_student_class(self, classe):
        try:
            classe.write({
                'number_of_student': len(classe.student_ids.ids),
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

    def action_update_all_student_class(self):
        active_ids = self.env.context.get('active_ids', [])
        classes = self.env['siantou.ems.core.class'].browse(active_ids)
        classes = list(classes)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')

        for classe in classes:
            self.add_number_of_student_class(classe)

        classes = list(classes)
        self.remove_duplicate_student_class(classes)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_open_copier(self):
        view_id = self.env.ref('siantou_ems_core.class_ue_copy_wizard').id
        return {
            'name': 'Copie des unités d\'enseignement',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'class.ue.copy.wizard',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': {
                'default_source_year_id': self.env['siantou.ems.core.year'].search([('is_active', '=', True)], limit=1).id,
            },
        }

class EducationClassGroup(models.Model):
    _name = 'siantou.ems.core.class.group'
    _description = 'Groupe de classe'

    name = fields.Char(string='Nom', required=True,
                       help="Entrer le nom du groupe")

    class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe',
        ondelete='cascade'
    )
