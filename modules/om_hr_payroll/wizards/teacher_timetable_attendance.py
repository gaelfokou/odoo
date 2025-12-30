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

    level_id = fields.Many2one(
        'siantou.ems.core.level',
        string='Niveau',
        related='class_id.level_id',
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

    identifier = fields.Char(
        'Matricule',
        related='employee_id.identifier',
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

    # Volume horaire du cours
    hours_credit = fields.Float(
        'Volume horaire du cours',
        default=0.0,
    )

    # Volume horaire du cours
    total_all = fields.Float(
        'Volume horaire programmé',
        default=0.0,
    )

    # Volume horaire effectué du cours
    total_done = fields.Float(
        'Volume horaire effectué',
        default=0.0,
    )

    # Volume horaire restant du cours
    total_awaiting = fields.Float(
        'Volume horaire restant',
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

    is_paid = fields.Boolean(
        'Payé',
        default=False,
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

    def _default_start_date(self):
        start_date = date.today().replace(day=1)
        return start_date

    start_date = fields.Date(
        'Date de début',
        default=_default_start_date,
    )

    def _default_end_date(self):
        end_date = (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()
        return end_date

    end_date = fields.Date(
        'Date de fin',
        default=_default_end_date,
    )

    day_of_week = fields.Selection([
            ('0', 'Lundi'),
            ('1', 'Mardi'),
            ('2', 'Mercredi'),
            ('3', 'Jeudi'),
            ('4', 'Vendredi'),
            ('5', 'Samedi'),
            ('6', 'Dimanche'),
        ],
        'Jour de la semaine',
        compute='_compute_day_of_week',
        store=True
    )

    @api.depends('date')
    def _compute_day_of_week(self):
        for record in self:
            if record.date:
                record.day_of_week = str(record.date.weekday())
            else:
                record.day_of_week = None

    @api.onchange('date')
    def _onchange_day_of_week(self):
        for record in self:
            if record.date:
                record.day_of_week = str(record.date.weekday())
            else:
                record.day_of_week = None

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
            if record.start_time < 0.0 or record.end_time < 0.0 or record.start_time > 23.59 or record.end_time > 23.59:
                raise ValidationError("Vous devez définir des heures de début et de fin corrects")
            elif record.start_time > record.end_time:
                raise ValidationError("L'heure de fin du cours doit être supérieure à l'heure de début du cours")

    # Contrainte logique pour s'assurer que les heures de début et de fin sont définies et que l'heure de fin est supérieure à l'heure de début
    @api.constrains('status', 'worked_start_time', 'worked_end_time')
    def _constrains_worked_time(self):
        for record in self:
            if record.worked_start_time < 0.0 or record.worked_end_time < 0.0 or record.worked_start_time > 23.59 or record.worked_end_time > 23.59:
                raise ValidationError("Vous devez définir des heures de début effectuée et de fin effectuée corrects")
            elif record.status in ['present', 'permission'] and record.worked_start_time > record.worked_end_time:
                raise ValidationError("L'heure de fin effectuée du cours doit être supérieure à l'heure de début effectuée du cours")

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
                'default_has_rate': False,
            },
        }

    def action_reset_filter(self):
        self.env['teacher.timetable.attendance']._transient_vacuum()
        self.env['teacher.timetable.attendance'].search([('create_uid', '=', self.env.user.id)]).unlink()
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
        domains = [
            ('id', 'in', active_ids)
        ]
        data = report_data.print_teacher_timetable_attendance_report_data(domains=domains)

        # Appeler le rapport PDF
        if len(data['docdata']['teacher_timetable_attendance_data'].keys()) == 0:
            raise UserError('Aucune donnée trouvée')
        report_action = self.env.ref('om_hr_payroll.action_report_teacher_timetable_attendance')
        return report_action.report_action(self, data=data)

    def action_print_resume_pdf(self):
        active_ids = self.env.context.get('active_ids', [])
        teacher_timetable_attendances = self.env['teacher.timetable.attendance'].browse(active_ids)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')
        report_data = self.env['teacher.timetable.attendance.print.wizard'].create({})
        domains = [
            ('id', 'in', active_ids)
        ]
        resume = True
        data = report_data.print_teacher_timetable_attendance_report_data(resume=resume, domains=domains)

        # Appeler le rapport PDF
        if len(data['docdata']['teacher_timetable_attendance_data'].keys()) == 0:
            raise UserError('Aucune donnée trouvée')
        report_action = self.env.ref('om_hr_payroll.action_report_teacher_timetable_attendance_resume')
        return report_action.report_action(self, data=data)

    def action_pay_done(self):
        active_ids = self.env.context.get('active_ids', [])
        teacher_timetable_attendances = self.env['teacher.timetable.attendance'].browse(active_ids)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')
        report_data = self.env['teacher.timetable.attendance.print.wizard'].create({})
        domains = [
            ('id', 'in', active_ids)
        ]
        resume = True
        data = report_data.print_teacher_timetable_attendance_report_data(resume=resume, domains=domains)

        # Appeler le rapport PDF
        if len(data['docdata']['teacher_timetable_attendance_data'].keys()) == 0:
            raise UserError('Aucune donnée trouvée')
        from_date = None
        to_date = None
        employee_ids = []
        teacher_timetable_attendance_data = dict(sorted(data['docdata']['teacher_timetable_attendance_data'].items(), key=lambda item: item[1]['name']))
        for key in teacher_timetable_attendance_data.keys():
            timetables = teacher_timetable_attendance_data[key]['data']
            for timetable in timetables:
                if 'start_date' in timetable:
                    from_date = timetable['start_date']
                if 'end_date' in timetable:
                    to_date = timetable['end_date']
                if 'employee_id' in timetable:
                    if timetable['employee_id'] not in employee_ids:
                        employee_ids.append(timetable['employee_id'])

        key_payslips = {}
        employees = self.env['hr.employee'].search([('id', 'in', employee_ids)])
        for employee in employees:
            if not employee.is_teacher:
                employee.write({
                    'is_teacher': True,
                })
            order = 'date_from asc'
            paymenthistories = self.env['hr.payslip'].search([('employee_id', '=', employee.id)], order=order)
            paymenthistories = list(paymenthistories)
            for paymenthistory in paymenthistories:
                for worked_days_line_id in paymenthistory.worked_days_line_ids:
                    end_time = TeacherTimetableAttendance.convert_float_to_time(worked_days_line_id.timetable_id.end_time, True)
                    start_time = TeacherTimetableAttendance.convert_float_to_time(worked_days_line_id.timetable_id.start_time, True)
                    key = '{}-{}-{}-{}'.format(worked_days_line_id.timetable_id.employee_id.id, worked_days_line_id.timetable_id.date, start_time, end_time)
                    if key not in key_payslips:
                        key_payslips[key] = {}
                        key_payslips[key]['timetable_id'] = worked_days_line_id.timetable_id.id
                        key_payslips[key]['rate'] = worked_days_line_id.rate
                        key_payslips[key]['amount'] = worked_days_line_id.amount

        timetable_ids = [payslip['timetable_id'] for payslip in key_payslips.values()]

        teacher_timetable_attendance_ids = []
        teacher_timetable_attendance_data = dict(sorted(data['docdata']['teacher_timetable_attendance_data'].items(), key=lambda item: item[1]['name']))
        for key in teacher_timetable_attendance_data.keys():
            timetables = teacher_timetable_attendance_data[key]['data']
            for timetable in timetables:
                if 'timetable_id' in timetable and timetable['timetable_id'] not in timetable_ids:
                    teacher_timetable_attendance_ids.append(timetable)

        if len(teacher_timetable_attendance_ids) == 0:
            raise UserError('Aucune donnée trouvée')

        payslips = self.env['hr.payslip']
        payslips._save_teacher_timetable_attendances(teacher_timetable_attendance_ids)
        for employee in employees:
            if employee.has_allowance_cd and employee.has_cnps:
                structure = self.env['ir.config_parameter'].sudo().get_param(f'siantou.code_structure_cd_cnps')
                if not structure:
                    structure = 'BASECDCNPS'
                    self.env['ir.config_parameter'].sudo().set_param(f'siantou.code_structure_cd_cnps', structure)
            elif employee.has_allowance_cd:
                structure = self.env['ir.config_parameter'].sudo().get_param(f'siantou.code_structure_cd')
                if not structure:
                    structure = 'BASECD'
                    self.env['ir.config_parameter'].sudo().set_param(f'siantou.code_structure_cd', structure)
            elif employee.has_allowance_co and employee.has_cnps:
                structure = self.env['ir.config_parameter'].sudo().get_param(f'siantou.code_structure_co_cnps')
                if not structure:
                    structure = 'BASECOCNPS'
                    self.env['ir.config_parameter'].sudo().set_param(f'siantou.code_structure_co_cnps', structure)
            elif employee.has_allowance_co:
                structure = self.env['ir.config_parameter'].sudo().get_param(f'siantou.code_structure_co')
                if not structure:
                    structure = 'BASECO'
                    self.env['ir.config_parameter'].sudo().set_param(f'siantou.code_structure_co', structure)
            elif employee.has_cnps:
                structure = self.env['ir.config_parameter'].sudo().get_param(f'siantou.code_structure_cnps')
                if not structure:
                    structure = 'BASECNPS'
                    self.env['ir.config_parameter'].sudo().set_param(f'siantou.code_structure_cnps', structure)
            else:
                structure = self.env['ir.config_parameter'].sudo().get_param(f'siantou.code_structure')
                if not structure:
                    structure = 'BASE'
                    self.env['ir.config_parameter'].sudo().set_param(f'siantou.code_structure', structure)
            struct_id = self.env['hr.payroll.structure'].search([('code', '=', structure)], limit=1)
            if not struct_id:
                raise UserError(_("You must select structure(s) to generate payslip(s)."))

            journal = self.env['ir.config_parameter'].sudo().get_param(f'siantou.code_journal')
            if not journal:
                journal = 'CSH1'
                self.env['ir.config_parameter'].sudo().set_param(f'siantou.code_journal', journal)
            journal_id = self.env['account.journal'].search([('code', '=', journal)], limit=1)
            if not journal_id:
                raise UserError(_("You must select journal(s) to generate payslip(s)."))

            slip_data = self.env['hr.payslip'].onchange_employee_id(from_date, to_date, employee.id, contract_id=False)

            if employee.has_allowance_cd and employee.has_cnps:
                contract = '{} (CDCNPS)'.format(employee.name)
            elif employee.has_allowance_cd:
                contract = '{} (CD)'.format(employee.name)
            elif employee.has_allowance_co and employee.has_cnps:
                contract = '{} (COCNPS)'.format(employee.name)
            elif employee.has_allowance_co:
                contract = '{} (CO)'.format(employee.name)
            elif employee.has_cnps:
                contract = '{} (CNPS)'.format(employee.name)
            else:
                contract = '{}'.format(employee.name)
            contract_id = self.env['hr.contract'].search([('name', '=', contract)], limit=1)
            if not contract_id:
                contract_id = self.env['hr.contract'].create({
                    'employee_id': employee.id,
                    'name': contract,
                    'date_start': from_date,
                    'struct_id': slip_data['value'].get('struct_id') or struct_id.id,
                    'wage': 0.0,
                    'company_id': slip_data['value'].get('company_id'),
                })

            res = {
                'employee_id': employee.id,
                'name': slip_data['value'].get('name'),
                'struct_id': slip_data['value'].get('struct_id') or struct_id.id,
                'contract_id': slip_data['value'].get('contract_id') or contract_id.id,
                'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids')],
                'date_from': from_date,
                'date_to': to_date,
                'company_id': employee.company_id.id,
                'journal_id': journal_id.id,
                'code': 'BASIC',
            }
            payslips += self.env['hr.payslip'].create(res)
        payslips.compute_sheet()

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
