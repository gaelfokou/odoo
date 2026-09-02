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

STATUS_PROGRESSREPORT = {
    'progressreport_available': 'Fiches de progression disponibles',
    'progressreport_not_available': 'Fiches de progression pas disponibles',
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
        related='specialty_id.field_of_study_id'
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

    status = fields.Selection([
        ('progressreport_available', 'Fiches de progression disponibles'),
        ('progressreport_not_available', 'Fiches de progression pas disponibles'),
    ], string='Statut',
        # default='progressreport_available',
    )

    subject_id_domain = fields.Binary(compute='_compute_subject_domain', default=[])

    class_id_domain = fields.Binary(compute='_compute_class_domain', default=[])

    specialty_id_domain = fields.Binary(compute='_compute_specialty_domain', default=[])

    @api.depends('school_id')
    def _compute_specialty_domain(self):
        for record in self:
            domain = []
            if record.school_id.id:
                domain.append(('school_id', '=', record.school_id.id))
            record.specialty_id_domain = domain

    @api.depends('class_id')
    def _compute_subject_domain(self):
        for record in self:
            domain = []
            if record.class_id.id:
                ue_ids = record.class_id.ue_ids
                domain = [
                    ('ue_ids', 'in', ue_ids.ids)
                ]
            record.subject_id_domain = domain

    @api.depends('year_id', 'school_id', 'level_id', 'field_of_study_id', 'specialty_id', 'option_id', 'type_cour')
    def _compute_class_domain(self):
        for record in self:
            domain = []
            if record.year_id.id:
                domain.append(('year_id', '=', record.year_id.id))
            if record.school_id.id:
                domain.append(('school_id', '=', record.school_id.id))
            if record.level_id.id:
                domain.append(('level_id', '=', record.level_id.id))
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

    def action_print_progress_pdf(self):
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
        if self.specialty_id.id:
            domain.append(('specialty_id', '=', self.specialty_id.id))
            title.append(self.specialty_id.name)
        if self.option_id.id:
            domain.append(('option_id', '=', self.option_id.id))
            title.append(self.option_id.name)
        if self.type_cour:
            domain.append(('class_id.type_cour', '=', self.type_cour))
            title.append(TYPE_COUR[self.type_cour])
        if self.class_id.id:
            domain.append(('class_id', '=', self.class_id.id))
            title.append(self.class_id.name)
        if self.subject_id.id:
            domain.append(('subject_id', '=', self.subject_id.id))
            title.append(self.subject_id.name)
        domain.append(('status', '!=', 'pending'))

        order = 'date asc, id asc'

        timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
        timetables = list(timetables)

        key_timetables = {}
        for timetable in timetables:
            if not timetable.date or not timetable.day_of_week or not timetable.employee_id.id:
                continue

            end_time = ProgressReportFilterWizard.convert_float_to_time(timetable.end_time, has_second=True)
            start_time = ProgressReportFilterWizard.convert_float_to_time(timetable.start_time, has_second=True)
            key = '{}-{}-{}-{}'.format(timetable.employee_id.id, timetable.date, start_time, end_time)
            if key not in key_timetables:
                key_timetables[key] = {}
                key_timetables[key]['timetable'] = timetable
            else:
                continue

        key_timetable_progressreports = {}
        for key in key_timetables.keys():
            k = '{}'.format(key_timetables[key]['timetable'].employee_id.id)
            if k not in key_timetable_progressreports:
                key_timetable_progressreports[k] = {}
                key_timetable_progressreports[k]['id'] = key_timetables[key]['timetable'].employee_id.id
                key_timetable_progressreports[k]['name'] = key_timetables[key]['timetable'].employee_id.name
                key_timetable_progressreports[k]['available'] = len(key_timetables[key]['timetable'].session_ids.ids)
                key_timetable_progressreports[k]['total'] = 1
                key_timetable_progressreports[k]['percentage'] = 0.0
                key_timetable_progressreports[k]['class'] = ''
            else:
                key_timetable_progressreports[k]['available'] += len(key_timetables[key]['timetable'].session_ids.ids)
                key_timetable_progressreports[k]['total'] += 1

        for key in key_timetable_progressreports.keys():
            if key_timetable_progressreports[key]['total'] > 0:
                key_timetable_progressreports[key]['percentage'] = (key_timetable_progressreports[key]['available'] / key_timetable_progressreports[key]['total']) * 100
                key_timetable_progressreports[key]['percentage'] = round(key_timetable_progressreports[key]['percentage'], 2)

        for key in key_timetable_progressreports.keys():
            if key_timetable_progressreports[key]['percentage'] >= 90.0:
                key_timetable_progressreports[key]['class'] = 'text-success'
            if key_timetable_progressreports[key]['percentage'] >= 80.0 and key_timetable_progressreports[key]['percentage'] < 90.0:
                key_timetable_progressreports[key]['class'] = 'text-warning'
            if key_timetable_progressreports[key]['percentage'] < 80.0:
                key_timetable_progressreports[key]['class'] = 'text-danger'

        key_progress_report_teachers = {}
        if self.status:
            if self.status == 'progressreport_available':
                title.append(STATUS_PROGRESSREPORT[self.status])
                for key in key_timetable_progressreports.keys():
                    if key_timetable_progressreports[key]['percentage'] > 0.0:
                        key_progress_report_teachers[key] = key_timetable_progressreports[key]
            elif self.status == 'progressreport_not_available':
                title.append(STATUS_PROGRESSREPORT[self.status])
                for key in key_timetable_progressreports.keys():
                    if key_timetable_progressreports[key]['percentage'] == 0.0:
                        key_progress_report_teachers[key] = key_timetable_progressreports[key]

        _logger.info(f'----------- tototototototo key_progress_report_teachers {key_progress_report_teachers} -----------')

        key_progress_report_teachers = sorted(key_progress_report_teachers.items(), key=self.sort_progress_report)
        key_progress_report_teachers = dict(key_progress_report_teachers)

        if len(title) > 0:
            title = ' / '.join(title)
        else:
            title = 'Non spécifié'

        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', title)

        filter_title = self.env['ir.config_parameter'].sudo().get_param(f'siantou.filter_user_{self.env.user.id}', '')

        title = 'Pourcentage de remplissage fiches de progression'

        if self.status:
            if self.status == 'progressreport_available':
                title = 'Pourcentage de remplissage fiches de progression disponibles'
            elif self.status == 'progressreport_not_available':
                title = 'Pourcentage de remplissage fiches de progression pas disponibles'

        data = {
            'docdata': {}
        }
        data['docdata']['title'] = title
        data['docdata']['filter'] = filter_title
        data['docdata']['progress_report_teacher_data'] = key_progress_report_teachers

        if self.school_id.id:
            data['docdata']['title'] = '{} {}'.format(data['docdata']['title'], self.school_id.name)
        if self.level_id.id:
            data['docdata']['title'] = '{} {}'.format(data['docdata']['title'], self.level_id.name)

        if len(data['docdata']['progress_report_teacher_data'].keys()) == 0:
            raise UserError('Aucune donnée trouvée')
        report_action = self.env.ref('siantou_ems_core.action_report_progress_report_teacher')
        report_action.update({
            'name': '{} PDF'.format(data['docdata']['title']),
        })
        return report_action.report_action(self, data=data)

    def action_print_percentage_pdf(self, sort_type=None, print_percentage=True):
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
        if self.specialty_id.id:
            domain.append(('specialty_id', '=', self.specialty_id.id))
            title.append(self.specialty_id.name)
        if self.option_id.id:
            domain.append(('option_id', '=', self.option_id.id))
            title.append(self.option_id.name)
        if self.type_cour:
            domain.append(('class_id.type_cour', '=', self.type_cour))
            title.append(TYPE_COUR[self.type_cour])
        if self.class_id.id:
            domain.append(('class_id', '=', self.class_id.id))
            title.append(self.class_id.name)
        if self.subject_id.id:
            domain.append(('subject_id', '=', self.subject_id.id))
            title.append(self.subject_id.name)

        order = 'date asc, id asc'

        timetables = self.env['siantou.ems.timetable.timetable'].search(domain, order=order).sorted(lambda rec: (rec.date, rec.id))
        timetables = list(timetables)

        timetable_ids = []
        key_timetables = {}
        for timetable in timetables:
            if not timetable.date or not timetable.day_of_week or not timetable.employee_id.id:
                continue

            end_time = ProgressReportFilterWizard.convert_float_to_time(timetable.end_time, has_second=True)
            start_time = ProgressReportFilterWizard.convert_float_to_time(timetable.start_time, has_second=True)
            if timetable.class_group_id.id:
                key = '{}-{}-{}-{}-{}'.format(timetable.class_id.id, timetable.class_group_id.id, timetable.date, start_time, end_time)
            else:
                key = '{}-{}-{}-{}'.format(timetable.class_id.id, timetable.date, start_time, end_time)
            if key not in key_timetables:
                key_timetables[key] = timetable
            else:
                continue

            timetable_ids.append(timetable.id)
        timetable_ids = list(set(timetable_ids))

        domain = []
        if self.class_id.id:
            domain.append(('class_id', '=', self.class_id.id))
        if self.subject_id.id:
            domain.append(('subject_id', '=', self.subject_id.id))

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
            exist_timetable_ids = []
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
                exist_timetable_ids.append(session['timetable_id'])
                if len(timetable_ids) > 0:
                    res = list(set(exist_timetable_ids) & set(timetable_ids))
                    if len(res) == 0:
                        del(key_employees[key_employee]['data'][key_progress_report])

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
                    progress_report_percentages[key_employee]['percentage'] = 0.0
                    progress_report_percentages[key_employee]['class'] = ''
                else:
                    percentage += key_employees[key_employee]['data'][key_progress_report]
                percentage_count += 1

            if percentage_count > 0:
                progress_report_percentages[key_employee]['percentage'] = percentage / percentage_count
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

        if sort_type:
            if sort_type == 'top':
                title = 'Pourcentage progression Top 10'
            else:
                title = 'Pourcentage progression Last 10'
        else:
            title = 'Pourcentage progression'

        data = {
            'docdata': {}
        }
        data['docdata']['title'] = title
        data['docdata']['filter'] = filter_title
        data['docdata']['progress_report_percentages'] = progress_report_percentages
        data['docdata']['sort_type'] = sort_type

        if self.school_id.id:
            data['docdata']['title'] = '{} {}'.format(data['docdata']['title'], self.school_id.name)
        if self.level_id.id:
            data['docdata']['title'] = '{} {}'.format(data['docdata']['title'], self.level_id.name)

        if print_percentage:
            report_action = self.env.ref('siantou_ems_core.action_report_progress_report_percentage')
            report_action.update({
                'name': '{} PDF'.format(data['docdata']['title']),
            })
            return report_action.report_action(self, data=data)
        else:
            return data

    def action_print_top_percentage_pdf(self):
        data = self.action_print_percentage_pdf(sort_type='top', print_percentage=False)

        report_action = self.env.ref('siantou_ems_core.action_report_progress_report_percentage')
        report_action.update({
            'name': '{} PDF'.format(data['docdata']['title']),
        })
        return report_action.report_action(self, data=data)

    def action_print_last_percentage_pdf(self):
        data = self.action_print_percentage_pdf(sort_type='last', print_percentage=False)

        report_action = self.env.ref('siantou_ems_core.action_report_progress_report_percentage')
        report_action.update({
            'name': '{} PDF'.format(data['docdata']['title']),
        })
        return report_action.report_action(self, data=data)

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
