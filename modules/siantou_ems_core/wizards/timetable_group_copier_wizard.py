from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from pprint import pformat
import pandas as pd
import numpy as np
import re
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import copy
import logging

DATE_FORMAT = '%Y-%m-%d'
DATE_FORMAT_FR = '%d/%m/%Y'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATETIME_FORMAT_FR = '%d/%m/%Y %H:%M'
TIME_FORMAT = '%H:%M:%S'
TIME_FORMAT_FR = '%H:%M'

STATUS_TIMETABLE = {
    'pending': 'En attente',
    'progress': 'En cours',
    'present': 'Présent',
    'absent': 'Absent',
    'permission': 'Permission',
    'exception': 'Exception',
    'delay': 'Retard',
}

TYPE_COUR = {
    'cj': 'Cours du jour',
    'cs': 'Cours du soir',
}

_logger = logging.getLogger(__name__)

class TimetableGroupCopierWizard(models.TransientModel):
    _name = 'timetable.group.copier.wizard'
    _description = 'Copieur des versions d\'emploi du temps'

    source_year_id = fields.Many2one(
        'siantou.ems.core.year',
        'Année académique source',
        required=True,
    )

    destination_year_id = fields.Many2one(
        'siantou.ems.core.year',
        'Année académique destination',
        required=True,
    )

    # Version auquel appartient l'emploi du temps
    group_id = fields.Many2one(
        'siantou.ems.timetable.group',
        'Version',
        required=True,
    )

    @api.onchange('source_year_id')
    def _onchange_group(self):
        for record in self:
            record.group_id = None

    def action_copier(self):
        domain = []
        if self.group_id.id:
            domain.append(('id', '=', self.group_id.id))

        group_id = self.env['siantou.ems.timetable.group'].search(domain, limit=1)
        if group_id:
            years = group_id.semester_id.year_id.name.split('-')
            years = [int(y) for y in years]
            new_years = self.destination_year_id.name.split('-')
            new_years = [int(y) for y in new_years]

            semester_id = self.env['siantou.ems.core.year.semester'].search([
                ('name', '=', group_id.semester_id.name),
                ('year_id', '=', self.destination_year_id.id),
            ], limit=1)
            if not semester_id:
                year, week, day = group_id.semester_id.start_time.isocalendar()
                try:
                    index_year = years.index(year)
                except ValueError:
                    index_year = -1
                if index_year != -1 and len(years) > 1 and len(new_years) > 1:
                    year = new_years[index_year]
                start_time = date.fromisocalendar(year, week, day)

                year, week, day = group_id.semester_id.end_time.isocalendar()
                try:
                    index_year = years.index(year)
                except ValueError:
                    index_year = -1
                if index_year != -1 and len(years) > 1 and len(new_years) > 1:
                    year = new_years[index_year]
                end_time = date.fromisocalendar(year, week, day)
                semester_id = self.env['siantou.ems.core.year.semester'].create({
                    'name': group_id.semester_id.name,
                    'start_time': start_time,
                    'end_time': end_time,
                    'year_id': self.destination_year_id.id,
                })
                level_ids = [(4, level_id.id) for level_id in group_id.semester_id.level_ids]
                # semester_id.level_ids = level_ids
                semester_id.write({'level_ids': level_ids })

            unique_string = datetime.now().strftime("%Y%m%d%H%M%S")
            name = '{} copie {}'.format(group_id.name, unique_string)
            new_group = self.env['siantou.ems.timetable.group'].create({
                'name': name,
                'semester_id': semester_id.id,
            })

            for timetable_id in group_id.timetable_ids:
                year, week, day = timetable_id.date.isocalendar()
                try:
                    index_year = years.index(year)
                except ValueError:
                    index_year = -1
                if index_year != -1 and len(years) > 1 and len(new_years) > 1:
                    year = new_years[index_year]
                start_date = date.fromisocalendar(year, week, day)
                class_id = self.env['siantou.ems.core.class'].search([
                    ('school_id', '=', timetable_id.school_id.id),
                    ('field_of_study_id', '=', timetable_id.field_of_study_id.id),
                    ('specialty_id', '=', timetable_id.specialty_id.id),
                    ('option_id', '=', timetable_id.option_id.id),
                    ('level_id', '=', timetable_id.level_id.id),
                    ('year_id', '=', self.destination_year_id.id),
                    ('type_cour', '=', timetable_id.type_cour),
                ], limit=1)
                if not class_id:
                    class_id = self.env['siantou.ems.core.class'].create({
                        'school_id': timetable_id.school_id.id,
                        'field_of_study_id': timetable_id.field_of_study_id.id,
                        'specialty_id': timetable_id.specialty_id.id,
                        'option_id': timetable_id.option_id.id,
                        'level_id': timetable_id.level_id.id,
                        'year_id': self.destination_year_id.id,
                        'type_cour': timetable_id.type_cour,
                    })
                    for group_id in timetable_id.class_id.group_ids:
                        class_id.group_ids.create({
                            'name': group_id.name,
                            'class_id': class_id.id,
                        })
                    ue_ids = []
                    for ue_id in timetable_id.class_id.ue_ids:
                        ue = self.env['siantou.ems.core.unite.enseignement'].search([
                            ('code', '=', ue_id.code),
                            ('semestre_id', '=', semester_id.id),
                        ], limit=1)
                        if not ue:
                            ue = self.env['siantou.ems.core.unite.enseignement'].create({
                                'code': ue_id.code,
                                'name': ue_id.name,
                                'type_ue': ue_id.type_ue,
                                'semestre_id': semester_id.id,
                            })
                            subject_ids = [(4, subject_id.id) for subject_id in ue_id.subject_ids]
                            ue.write({'subject_ids': subject_ids })
                            for syllabus_id in ue_id.syllabus_ids:
                                self.env['siantou.ems.core.syllabus'].create({
                                    'name': syllabus_id.name,
                                    'ue_id': ue.id,
                                    'subject_id': syllabus_id.subject_id.id,
                                    'class_id': class_id.id,
                                    'description': syllabus_id.description,
                                    'pourcentage_cc': syllabus_id.pourcentage_cc,
                                    'pourcentage_exam': syllabus_id.pourcentage_exam,
                                    'pourcentage_presence': syllabus_id.pourcentage_presence,
                                    'note_sn': syllabus_id.note_sn,
                                    'coefficient': syllabus_id.coefficient,
                                    'note_sn': syllabus_id.note_sn,
                                    'cm': syllabus_id.cm,
                                    'tp': syllabus_id.tp,
                                    'td': syllabus_id.td,
                                    'te': syllabus_id.te,
                                    # 'pro_pe_id': syllabus_id.pro_pe_id,
                                })
                        ue_ids.append(ue)
                    ue_ids = [(4, ue_id.id) for ue_id in ue_ids]
                    class_id.write({'ue_ids': ue_ids })
                self.env['siantou.ems.timetable.timetable'].create({
                    'department_id': timetable_id.field_of_study_id.department_id.id,
                    'school_id': timetable_id.school_id.id,
                    'level_id': timetable_id.level_id.id,
                    'specialty_id': timetable_id.specialty_id.id,
                    'option_id': timetable_id.option_id.id,
                    'class_id': class_id.id,
                    'class_group_id': timetable_id.class_group_id.id,
                    'ue_id': timetable_id.ue_id.id,
                    'subject_id': timetable_id.subject_id.id,
                    'building_id': timetable_id.building_id.id,
                    'classroom_id': timetable_id.classroom_id.id,
                    'employee_id': timetable_id.employee_id.id,
                    'date': start_date,
                    'start_time': timetable_id.start_time,
                    'end_time': timetable_id.end_time,
                    'group_id': new_group.id,
                })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
