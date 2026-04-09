from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from pprint import pformat
import pandas as pd
import numpy as np
import re
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import copy
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
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

STATUS_CLASS = {
    'timetable_available': 'Emplois du temps disponibles',
    'timetable_not_available': 'Emplois du temps pas disponibles',
    'student_available': 'Étudiants disponibles',
    'student_not_available': 'Étudiants pas disponibles',
    'student_more_than_or_equal': 'Étudiants plus de ou égal à',
    'student_less_than': 'Étudiants moins de',
}

_logger = logging.getLogger(__name__)

class ProgressReportFilterWizard(models.TransientModel):
    _name = 'progress.report.filter.wizard'
    _description = 'Filtre des fiches de progression'

    year_id = fields.Many2one(
        'siantou.ems.core.year',
        'Année académique',
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

    specialty_id = fields.Many2one(
        'siantou.ems.core.specialty',
        string='Spécialité',
    )

    option_id = fields.Many2one(
        'siantou.ems.core.option',
        string='Option',
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

    subject_id_domain = fields.Binary(compute='_compute_class_domain', default=[])

    class_id_domain = fields.Binary(compute='_compute_all_domain', default=[])

    specialty_id_domain = fields.Binary(compute='_compute_school_domain', default=[])

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

    @api.onchange('school_id')
    def _onchange_school(self):
        for record in self:
            record.field_of_study_id = None
            record.level_id = None
            record.specialty_id = None
            record.option_id = None
            record.class_id = None
            record.subject_id = None

    @api.onchange('specialty_id')
    def _onchange_specialty(self):
        for record in self:
            record.option_id = None
            record.class_id = None
            record.subject_id = None

    @api.onchange('option_id')
    def _onchange_option(self):
        for record in self:
            record.class_id = None
            record.subject_id = None

    @api.onchange('class_id')
    def _onchange_class(self):
        for record in self:
            record.subject_id = None

    def action_filter(self):
        domain = []
        title = []
        if self.year_id.id:
            domain.append(('year_id', '=', self.year_id.id))
            title.append(self.year_id.name)
        if self.school_id.id:
            domain.append(('school_id', '=', self.school_id.id))
            title.append(self.school_id.name)
        if self.field_of_study_id.id:
            domain.append(('field_of_study_id', '=', self.field_of_study_id.id))
            title.append(self.field_of_study_id.name)
        if self.level_id.id:
            domain.append(('level_id', '=', self.level_id.id))
            title.append(self.level_id.name)
        if self.specialty_id.id:
            domain.append(('specialty_id', '=', self.specialty_id.id))
            title.append(self.specialty_id.name)
        if self.option_id.id:
            domain.append(('option_id', '=', self.option_id.id))
            title.append(self.option_id.name)
        if self.type_cour:
            domain.append(('type_cour', '=', self.type_cour))
            title.append(TYPE_COUR[self.type_cour])

        class_ids = []
        classes = self.env['siantou.ems.core.class'].search(domain)
        for classe in classes:
            class_ids.append(classe.id)
        class_ids = list(set(class_ids))

        domain = [
            ('class_id', 'in', class_ids),
        ]

        if self.class_id.id:
            domain.append(('class_id', '=', self.class_id.id))
            title.append(self.class_id.name)
        if self.subject_id.id:
            domain.append(('subject_id', '=', self.subject_id.id))
            title.append(self.subject_id.name)

        report_ids = []
        reports = self.env['siantou.ems.core.progress.report'].search(domain)
        for report in reports:
            report_ids.append(report.id)
        report_ids = list(set(report_ids))

        domain = [
            ('id', 'in', report_ids),
        ]

        if len(title) > 0:
            title = ' / '.join(title)
        else:
            title = 'Non spécifié'

        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', title)

        view_id = self.env.ref('siantou_ems_core.progress_report_tree_view').id
        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'siantou.ems.core.progress.report',
            'views': [(view_id, 'tree'), (False, 'form')],
            'view_id': view_id,
            'domain': domain,
            'target': 'main',
        }

    def sort_progress_report_percentage(self, progress_report_percentage):
        percentage = progress_report_percentage[1]['percentage']
        return percentage

    def sort_progress_report(self, progress_report_percentage):
        name = progress_report_percentage[1]['name'] if progress_report_percentage[1]['name'] else ''
        name = name.strip()
        name = name.lower()
        return name

    def action_print_percentage_pdf(self, sort_type=None):
        domain = []
        title = []
        if self.year_id.id:
            domain.append(('year_id', '=', self.year_id.id))
            title.append(self.year_id.name)
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
        if self.class_id.id:
            domain.append(('class_id', '=', self.class_id.id))
            title.append(self.class_id.name)
        if self.subject_id.id:
            domain.append(('subject_id', '=', self.subject_id.id))
            title.append(self.subject_id.name)

        report_ids = []
        reports = self.env['siantou.ems.core.progress.report'].search(domain)
        for report in reports:
            report_ids.append(report.id)
        report_ids = list(set(report_ids))

        domain = [
            ('id', 'in', report_ids),
        ]

        if len(title) > 0:
            title = ' / '.join(title)
        else:
            title = 'Non spécifié'

        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', title)

        if len(report_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')
        report_data = self.env['progress.report.print.wizard'].create({})
        data = report_data.print_progress_report_data(domains=domain, sort_type=sort_type)

        if len(data['docdata']['report_data']) == 0:
            raise UserError('Aucune donnée trouvée')

        key_employees = {}
        for report in data['docdata']['report_data']:
            for session in report['sessions']:
                key_employee = '{}'.format(session['employee_id'])
                key_progress_report = '{}'.format(session['report_id'])
                if key_employee not in key_employees:
                    key_employees[key_employee] = {}
                    key_employees[key_employee]['name'] = session['employee_name']
                    key_employees[key_employee]['data'] = {}
                    key_employees[key_employee]['data'][key_progress_report] = report['percentage']
                else:
                    if key_progress_report not in key_employees[key_employee]['data']:
                        key_employees[key_employee]['data'][key_progress_report] = report['percentage']

        list_progress_report_percentages = []
        progress_report_percentages = {}
        for key_employee in key_employees.keys():
            percentage = 0.0
            percentage_count = 0
            for key_progress_report in key_employees[key_employee]['data'].keys():
                if key_employee not in progress_report_percentages:
                    progress_report_percentages[key_employee] = {}
                    progress_report_percentages[key_employee]['name'] = key_employees[key_employee]['name']
                    percentage += key_employees[key_employee]['data'][key_progress_report]
                    progress_report_percentages[key_employee]['class'] = ''
                else:
                    percentage += key_employees[key_employee]['data'][key_progress_report]
                percentage_count += 1

            progress_report_percentages[key_employee]['percentage'] = 0.0
            if percentage_count > 0:
                progress_report_percentages[key_employee]['percentage'] = (percentage / percentage_count) * 100
                progress_report_percentages[key_employee]['percentage'] = round(progress_report_percentages[key_employee]['percentage'], 2)
                if progress_report_percentages[key_employee]['percentage'] not in list_progress_report_percentages:
                    list_progress_report_percentages.append(progress_report_percentages[key_employee]['percentage'])

        for key in progress_report_percentages.keys():
            if progress_report_percentages[key]['percentage'] >= 90.0:
                progress_report_percentages[key]['class'] = 'text-success'
            if progress_report_percentages[key]['percentage'] >= 80.0 and progress_report_percentages[key]['percentage'] < 90.0:
                progress_report_percentages[key]['class'] = 'text-warning'
            if progress_report_percentages[key]['percentage'] < 80.0:
                progress_report_percentages[key]['class'] = 'text-danger'

        if sort_type:
            list_progress_report_percentages = list(set(list_progress_report_percentages))
            list_progress_report_percentages = sorted(list_progress_report_percentages, key=lambda x: x, reverse=True)
            if len(list_progress_report_percentages) > 0:
                if sort_type == 'top':
                    list_progress_report_percentages = list_progress_report_percentages[:10]
                else:
                    list_progress_report_percentages = list_progress_report_percentages[-10:]

            key_list_progress_report_percentages = {}
            for key in progress_report_percentages.keys():
                if progress_report_percentages[key]['percentage'] in list_progress_report_percentages:
                    key_list_progress_report_percentages[key] = progress_report_percentages[key]

            progress_report_percentages = key_list_progress_report_percentages

            progress_report_percentages = sorted(progress_report_percentages.items(), key=self.sort_progress_report_percentage, reverse=True)
            progress_report_percentages = dict(progress_report_percentages)
        else:
            progress_report_percentages = sorted(progress_report_percentages.items(), key=self.sort_progress_report)
            progress_report_percentages = dict(progress_report_percentages)

        if len(title) > 0:
            title = ' / '.join(title)
        else:
            title = 'Non spécifié'

        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', title)

        filter_title = self.env['ir.config_parameter'].sudo().get_param(f'siantou.filter_user_{self.env.user.id}', '')

        label = 'Enseignant'

        if sort_type:
            if sort_type == 'top':
                title = 'Pourcentage progression Top 10 par {}'.format(label)
            else:
                title = 'Pourcentage progression Last 10 par {}'.format(label)
        else:
            title = 'Pourcentage progression par {}'.format(label)

        data = {
            'docdata': {}
        }
        data['docdata']['label'] = label
        data['docdata']['title'] = title
        data['docdata']['filter'] = filter_title
        data['docdata']['progress_report_percentages'] = progress_report_percentages
        data['docdata']['sort_type'] = sort_type

        if self.school_id.id:
            data['docdata']['title'] = '{} {}'.format(data['docdata']['title'], self.school_id.name)

        report_action = self.env.ref('siantou_ems_core.action_report_progress_report_percentage')
        report_action.update({
            'name': '{} PDF'.format(title),
        })
        return report_action.report_action(self, data=data)

    def action_print_top_percentage_pdf(self):
        data = self.action_print_percentage_pdf(sort_type='top')

        start_date = datetime.strftime(self.start_date, DATE_FORMAT_FR)
        end_date = datetime.strftime(self.end_date, DATE_FORMAT_FR)

        report_action = self.env.ref('siantou_ems_core.action_report_progress_report_percentage')
        report_action.update({
            'name': '{} du {} - {} PDF'.format(data['docdata']['title'], start_date, end_date),
        })
        return report_action.report_action(self, data=data)

    def action_print_last_percentage_pdf(self):
        data = self.action_print_percentage_pdf(sort_type='last')

        start_date = datetime.strftime(self.start_date, DATE_FORMAT_FR)
        end_date = datetime.strftime(self.end_date, DATE_FORMAT_FR)

        report_action = self.env.ref('siantou_ems_core.action_report_progress_report_percentage')
        report_action.update({
            'name': '{} du {} - {} PDF'.format(data['docdata']['title'], start_date, end_date),
        })
        return report_action.report_action(self, data=data)
