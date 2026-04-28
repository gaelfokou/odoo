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

class TimetableGroupMoveWizard(models.TransientModel):
    _name = 'timetable.group.move.wizard'
    _description = 'Déplacement des versions d\'emploi du temps'

    year_id = fields.Many2one(
        'siantou.ems.core.year',
        'Année académique',
        required=True,
    )

    source_group_id = fields.Many2one(
        'siantou.ems.timetable.group',
        string='Version d\'emploi du temps source',
        required=True,
    )

    destination_group_id = fields.Many2one(
        'siantou.ems.timetable.group',
        string='Version d\'emploi du temps destination',
        required=True,
    )

    school_id = fields.Many2one(
        'siantou.ems.core.school',
        string='École',
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Département'
    )

    class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe',
    )

    is_submit = fields.Boolean(string='Soumis ?', default=True)

    start_date = fields.Date(
        string='Date de début',
    )

    end_date = fields.Date(
        string='Date de fin',
    )

    @api.constrains('start_date', 'end_date')
    def _constrains_date(self):
        for record in self:
            if record.start_date > record.end_date:
                raise ValidationError("La date de fin doit être supérieure à la date de début")

    @api.onchange('year_id')
    def _onchange_year(self):
        for record in self:
            record.source_group_id = None
            record.destination_group_id = None
            record.school_id = None
            record.department_id = None
            record.class_id = None

    @api.onchange('source_group_id')
    def _onchange_source_group(self):
        for record in self:
            record.destination_group_id = None
            record.school_id = None
            record.department_id = None
            record.class_id = None

    @api.onchange('school_id')
    def _onchange_school(self):
        for record in self:
            record.destination_group_id = None
            record.department_id = None
            record.class_id = None

    @api.onchange('department_id')
    def _onchange_department(self):
        for record in self:
            record.destination_group_id = None
            record.class_id = None

    @api.onchange('class_id')
    def _onchange_class(self):
        for record in self:
            record.destination_group_id = None

    school_id_domain = fields.Binary(compute='_compute_school_domain', default=[])

    department_id_domain = fields.Binary(compute='_compute_department_domain', default=[])

    class_id_domain = fields.Binary(compute='_compute_class_domain', default=[])

    destination_group_id_domain = fields.Binary(compute='_compute_destination_group_domain', default=[])

    @api.depends('source_group_id')
    def _compute_school_domain(self):
        for record in self:
            school_ids = record.source_group_id.school_ids
            domain = [
                ('id', 'in', school_ids.ids),
            ]
            record.school_id_domain = domain

    @api.depends('source_group_id', 'school_id')
    def _compute_department_domain(self):
        for record in self:
            department_ids = record.source_group_id.department_ids
            domain = [
                ('id', 'in', department_ids.ids),
            ]
            if record.school_id.id:
                domain.append(('school_id', '=', record.school_id.id))
            record.department_id_domain = domain

    @api.depends('source_group_id', 'school_id', 'department_id')
    def _compute_class_domain(self):
        for record in self:
            class_ids = record.source_group_id.class_ids
            domain = [
                ('id', 'in', class_ids.ids),
            ]
            if record.school_id.id:
                domain.append(('school_id', '=', record.school_id.id))
            if record.department_id.id:
                domain.append(('specialty_id.department_id', '=', record.department_id.id))
            record.class_id_domain = domain

    @api.depends('is_submit', 'source_group_id', 'school_id', 'department_id', 'class_id')
    def _compute_destination_group_domain(self):
        for record in self:
            domain = [
                ('is_submit', '=', record.is_submit),
                ('semester_id', '=', record.source_group_id.semester_id.id),
            ]
            if record.school_id.id:
                domain.append(('school_ids', '=', record.school_id.id))
            if record.department_id.id:
                domain.append(('department_ids', '=', record.department_id.id))
            if record.class_id.id:
                domain.append(('class_ids', '=', record.class_id.id))
            record.destination_group_id_domain = domain

    def action_move(self):
        source_group_id = self.env['siantou.ems.timetable.group'].search([('id', '=', self.source_group_id.id)], limit=1)
        if source_group_id:
            destination_group_id = self.env['siantou.ems.timetable.group'].search([('id', '=', self.destination_group_id.id)], limit=1)
            if destination_group_id:
                timetable_ids = source_group_id.timetable_ids
                if self.school_id.id:
                    timetable_ids = timetable_ids.filtered(lambda rec: rec.school_id.id and self.school_id.id)
                if self.department_id.id:
                    timetable_ids = timetable_ids.filtered(lambda rec: rec.department_id.id and self.department_id.id)
                if self.class_id.id:
                    timetable_ids = timetable_ids.filtered(lambda rec: rec.class_id.id and self.class_id.id)
                if self.start_date and self.end_date:
                    timetable_ids = timetable_ids.filtered(lambda rec: rec.date and rec.day_of_week and rec.date >= self.start_date and rec.date <= self.end_date)
                for timetable_id in timetable_ids:
                    timetable_id.write({
                        'group_id': destination_group_id.id,
                        'skip_validation': True,
                    })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
