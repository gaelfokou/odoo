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

class TeacherTimetableAttendance(models.TransientModel):
    _name = 'teacher.timetable.attendance'
    _description = 'Émargement d\'enseignant'
    _transient_max_count = 0
    _transient_max_hours = 0.2

    name = fields.Char(
        string='Nom',
        compute='_compute_name', store=True,
    )

    timetable_id = fields.Many2one(
        'siantou.ems.timetable.timetable',
        string='Emploi du temps',
        required=True,
    )

    class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe',
        related='timetable_id.class_id',
        store=True
    )

    subject_id = fields.Many2one(
        'siantou.ems.core.subject',
        'Cours',
        related='timetable_id.subject_id',
        store=True
    )

    # Enseignant lié à la programmation de cours
    employee_id = fields.Many2one(
        'hr.employee',
        'Enseignant',
        related='timetable_id.employee_id',
        store=True
    )

    is_teacher = fields.Boolean(
        'Est un enseignant',
        related='employee_id.is_teacher',
        store=True
    )

    is_permanent = fields.Boolean(
        'Est un permanent',
        related='employee_id.is_permanent',
        store=True
    )

    date = fields.Date(
        'Date',
        related='timetable_id.date',
        store=True
    )

    # Heure de début du cours
    start_time = fields.Float(
        'Heure de début',
        related='timetable_id.start_time',
        store=True
    )

    # Heure de fin du cours
    end_time = fields.Float(
        'Heure de fin',
        related='timetable_id.end_time',
        store=True
    )

    # Heure de début du cours
    worked_start_time = fields.Float(
        'Heure de début effectuée',
        related='timetable_id.worked_start_time',
        store=True
    )

    # Heure de fin du cours
    worked_end_time = fields.Float(
        'Heure de fin effectuée',
        related='timetable_id.worked_end_time',
        store=True
    )

    # Heure de fin du cours
    worked_time = fields.Float(
        'Heure effectuée',
        default=0.0,
    )

    status = fields.Selection([
        ('pending', 'En attente'),
        ('progress', 'En cours'),
        ('present', 'Présent'),
        ('absent', 'Absent'),
        ('permission', 'Permission'),
        ('exception', 'Exception'),
        ('delay', 'Retard'),
    ], 'Statut',
        related='timetable_id.status',
        store=True
    )

    # Taux de l\'enseignant
    rate = fields.Float(
        'Taux horaire',
        default=0.0,
    )

    amount = fields.Float(
        'Montant',
        default=0.0,
    )

    @api.depends('timetable_id')
    def _compute_name(self):
        for record in self:
            record.name = record.timetable_id.name

    @api.onchange('timetable_id')
    def _onchange_name(self):
        for record in self:
            record.name = record.timetable_id.name

    # Contrainte logique pour s'assurer que les heures de début et de fin sont définies et que l'heure de fin est supérieure à l'heure de début
    @api.constrains('start_time', 'end_time')
    def _constrains_time(self):
        for record in self:
            if record.end_time < record.start_time:
                raise ValidationError("L'heure de fin du cours doit être supérieure à l'heure de début du cours")

    def action_open_filter(self):
        view_id = self.env.ref('om_hr_payroll.teacher_timetable_attendance_filter_wizard').id
        return {
            'name': 'Filtre des émargements des enseignants',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'teacher.timetable.attendance.filter.wizard',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': {
                'default_status': 'present',
            },
        }

    def action_reset_filter(self):
        self.env['teacher.timetable.attendance']._transient_vacuum()
        self.env['teacher.timetable.attendance'].search([]).unlink()
        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', '')
        action = self.env.ref('om_hr_payroll.action_show_teacher_timetable_attendance').read()[0]
        action.update({
            'target': 'main',
        })
        return action

    def action_print_pdf(self):
        active_ids = self.env.context.get('active_ids', [])
        teacher_timetable_attendances = self.env['teacher.timetable.attendance'].browse(active_ids)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')
        report_data = self.env['teacher.timetable.attendance.print.wizard'].create({})
        domain = [
            ('id', 'in', active_ids)
        ]
        data = report_data.print_teacher_timetable_attendance_report_data(domain)

        # Appeler le rapport PDF
        if not data['docdata']['teacher_timetable_attendance_data']:
            raise UserError('Aucune donnée trouvée')
        report_action = self.env.ref('om_hr_payroll.action_report_teacher_timetable_attendance')
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
