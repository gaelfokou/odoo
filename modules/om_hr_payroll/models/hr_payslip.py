# -*- coding:utf-8 -*-
import babel
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
import pytz
import logging

UTC_TZ = pytz.utc

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
    '6': 'Dimanche',
}

_logger = logging.getLogger(__name__)

class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _description = 'Pay Slip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    struct_id = fields.Many2one('hr.payroll.structure', string='Structure',
        help='Defines the rules that have to be applied to this payslip, accordingly '
             'to the contract chosen. If you let empty the field contract, this field isn\'t '
             'mandatory anymore and thus the rules applied will be all the rules set on the '
             'structure of all contracts of the employee valid for the chosen period')
    name = fields.Char(string='Payslip Name')
    number = fields.Char(string='Reference', copy=False)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    date_from = fields.Date(string='Date From', required=True,
        default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date(string='Date To', required=True,
        default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    # this is chaos: 4 states are defined, 3 are used ('verify' isn't) and 5 exist ('confirm' seems to have existed)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('cancel', 'Rejected'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft',
        help="""* When the payslip is created the status is \'Draft\'
                \n* If the payslip is under verification, the status is \'Waiting\'.
                \n* If the payslip is confirmed then status is set to \'Done\'.
                \n* When user cancel payslip the status is \'Rejected\'.""")
    line_ids = fields.One2many('hr.payslip.line', 'slip_id', string='Payslip Lines')
    company_id = fields.Many2one(
        'res.company', string='Company', copy=False,
        default=lambda self: self.env.company
    )

    worked_days_line_ids = fields.One2many(
        'hr.payslip.worked_days', 'payslip_id',
        string='Payslip Worked Days', copy=True
    )

    input_line_ids = fields.One2many(
        'hr.payslip.input', 'payslip_id',
        string='Payslip Inputs', copy=True
    )

    paid = fields.Boolean(string='Made Payment Order ?', copy=False)
    note = fields.Text(string='Internal Note')
    contract_id = fields.Many2one('hr.contract', string='Contract')
    details_by_salary_rule_category = fields.One2many('hr.payslip.line',
        compute='_compute_details_by_salary_rule_category', string='Details by Salary Rule Category')
    credit_note = fields.Boolean(string='Credit Note ?',
        help="Indicates this payslip has a refund of another")
    payslip_run_id = fields.Many2one('hr.payslip.run', string='Payslip Batches', copy=False)
    payslip_count = fields.Integer(compute='_compute_payslip_count', string="Payslip Computation Details")

    # Calcul de la paie tenant compte des informations fournies par la biométrie
    total_hours = fields.Float(compute='_compute_total_hours', string='Total hours')
    code = fields.Char(help="The code that can be used in the salary rules")

    _teacher_timetable_attendances = []

    @staticmethod
    def _save_teacher_timetable_attendances(data):
        HrPayslip._teacher_timetable_attendances = data

    @staticmethod
    def convert_datetime_from_utc(dt):
        new_tz = pytz.timezone('Africa/Douala')
        old_tz = pytz.utc
        local_dt = old_tz.localize(dt)
        dt = local_dt.astimezone(new_tz)
        return dt

    @staticmethod
    def convert_datetime_to_utc(dt):
        old_tz = pytz.timezone('Africa/Douala')
        new_tz = pytz.utc
        local_dt = old_tz.localize(dt)
        dt = local_dt.astimezone(new_tz)
        return dt

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

    @staticmethod
    def convert_time_to_float(tm):
        tm = str(tm)
        tm = tm.split(':')
        tm = tm[0:2]
        tm = '.'.join(tm)
        tm = eval(tm)
        tm = float(tm)
        tm = round(tm, 2)
        return tm

    @staticmethod
    def increment_float_time(tm, n=0.0):
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
        tm = time(int(tm[0]), int(tm[1]))
        n = str(n)
        n = n.split('.')
        if len(n) == 1:
            n.append('0')
        if len(n[0]) == 1:
            n[0] = '0{}'.format(n[0])
        elif len(n[0]) > 2:
            n[0] = '{}'.format(n[0][0:2])
        if int(n[0]) > 23:
            n[0] = '00'
        if len(n[1]) == 1:
            n[1] = '{}0'.format(n[1])
        elif len(n[1]) > 2:
            n[1] = '{}'.format(n[1][0:2])
        if int(n[1]) > 59:
            n[1] = '00'
        tm = datetime.combine(date.min, tm) + timedelta(hours=int(n[0]), minutes=int(n[1]))
        tm = datetime.strftime(tm, TIME_FORMAT_FR)
        tm = HrPayslip.convert_time_to_float(tm)
        return tm

    def filter_daily_attendance(self, end_date, start_date, employee=None):
        min_start_time = self.env['ir.config_parameter'].sudo().get_param(f'siantou.min_start_time')
        if not min_start_time:
            min_start_time = '30'
            self.env['ir.config_parameter'].sudo().set_param(f'siantou.min_start_time', min_start_time)
        max_end_time = self.env['ir.config_parameter'].sudo().get_param(f'siantou.max_end_time')
        if not max_end_time:
            max_end_time = '15'
            self.env['ir.config_parameter'].sudo().set_param(f'siantou.max_end_time', max_end_time)
        min_start_time = int(min_start_time)
        max_end_time = int(max_end_time)
        # Filtre des données biométriques de l'enseignant pour une période donnée
        end_date = datetime.strftime(end_date, DATE_FORMAT)
        start_date = datetime.strftime(start_date, DATE_FORMAT)

        end_time = '23:00:00'
        start_time = '06:00:00'

        datetime_to = datetime.strptime(f"{end_date} {end_time}", DATETIME_FORMAT)
        datetime_from = datetime.strptime(f"{start_date} {start_time}", DATETIME_FORMAT)

        datetime_before = datetime_from - timedelta(minutes=max_end_time)
        # datetime_from = datetime_from + timedelta(minutes=max_end_time)

        datetime_after = datetime_to + timedelta(minutes=max_end_time)
        # datetime_to = datetime_to - timedelta(minutes=max_end_time)

        datetime_before = HrPayslip.convert_datetime_to_utc(datetime_before)
        # datetime_from = HrPayslip.convert_datetime_to_utc(datetime_from)
        datetime_after = HrPayslip.convert_datetime_to_utc(datetime_after)
        # datetime_to = HrPayslip.convert_datetime_to_utc(datetime_to)

        domain = [
            ('punch_type', 'in', ['0', '1', '255'])
        ]
        if employee:
            domain.append(('employee_id', '=', employee.id))

        daily_attendances = self.env['daily.attendance'].search(domain, order='punching_time asc').filtered(lambda rec: UTC_TZ.localize(rec.punching_time) >= datetime_before and UTC_TZ.localize(rec.punching_time) <= datetime_after).sorted(lambda rec: UTC_TZ.localize(rec.punching_time))
        daily_attendances = list(daily_attendances)

        return daily_attendances

    def filter_daily_attendance_teacher(self, current_date, end_time, start_time, employee=None):
        min_start_time = self.env['ir.config_parameter'].sudo().get_param(f'siantou.min_start_time')
        if not min_start_time:
            min_start_time = '30'
            self.env['ir.config_parameter'].sudo().set_param(f'siantou.min_start_time', min_start_time)
        max_end_time = self.env['ir.config_parameter'].sudo().get_param(f'siantou.max_end_time')
        if not max_end_time:
            max_end_time = '15'
            self.env['ir.config_parameter'].sudo().set_param(f'siantou.max_end_time', max_end_time)
        min_start_time = int(min_start_time)
        max_end_time = int(max_end_time)
        # Filtre des données biométriques de l'enseignant pour une période donnée
        current_date = datetime.strftime(current_date, DATE_FORMAT)

        end_time = HrPayslip.convert_float_to_time(end_time, has_second=True)
        start_time = HrPayslip.convert_float_to_time(start_time, has_second=True)

        datetime_to = datetime.strptime(f"{current_date} {end_time}", DATETIME_FORMAT)
        datetime_from = datetime.strptime(f"{current_date} {start_time}", DATETIME_FORMAT)

        datetime_before = datetime_from - timedelta(minutes=min_start_time)
        # datetime_from = datetime_from + timedelta(minutes=max_end_time)

        datetime_after = datetime_to + timedelta(minutes=max_end_time)
        # datetime_to = datetime_to - timedelta(minutes=max_end_time)

        datetime_before = HrPayslip.convert_datetime_to_utc(datetime_before)
        datetime_from = HrPayslip.convert_datetime_to_utc(datetime_from)
        datetime_after = HrPayslip.convert_datetime_to_utc(datetime_after)
        datetime_to = HrPayslip.convert_datetime_to_utc(datetime_to)

        daily_attendances = []

        domain = [
            ('punch_type', 'in', ['0', '255'])
        ]
        if employee:
            domain.append(('employee_id', '=', employee.id))

        daily_in_attendances = self.env['daily.attendance'].search(domain, order='punching_time asc').filtered(lambda rec: UTC_TZ.localize(rec.punching_time) >= datetime_before and UTC_TZ.localize(rec.punching_time) <= datetime_to).sorted(lambda rec: UTC_TZ.localize(rec.punching_time))
        daily_in_attendances = list(daily_in_attendances)
        if len(daily_in_attendances) > 0:
            daily_attendances.append(daily_in_attendances[0])

        domain = [
            ('punch_type', 'in', ['1', '255'])
        ]
        if employee:
            domain.append(('employee_id', '=', employee.id))

        daily_out_attendances = self.env['daily.attendance'].search(domain, order='punching_time asc').filtered(lambda rec: UTC_TZ.localize(rec.punching_time) >= datetime_from and UTC_TZ.localize(rec.punching_time) <= datetime_after).sorted(lambda rec: UTC_TZ.localize(rec.punching_time))
        daily_out_attendances = list(daily_out_attendances)
        if len(daily_out_attendances) > 0:
            daily_attendances.append(daily_out_attendances[-1])

        return daily_attendances

    def employee_total_hours(self, payslip):
        date_to = payslip.date_to
        date_from = payslip.date_from

        if date_to > date.today():
            date_to = date.today()

        if date_from > date_to:
            date_from = date_to

        # Calcul de la duréee d'un cours
        total_weekly_hours = 0.0

        if payslip.employee_id.id:
            if payslip.employee_id.is_teacher:
                if payslip.employee_id.is_permanent:
                    # Recherche des emplois du temps de l'enseignant pour une période donnée
                    for teacher_timetable_attendance in HrPayslip._teacher_timetable_attendances:
                        if payslip.employee_id.id == teacher_timetable_attendance['employee_id']:
                            total_weekly_hours += teacher_timetable_attendance['worked_time']
                else:
                    # Recherche des emplois du temps de l'enseignant pour une période donnée
                    for teacher_timetable_attendance in HrPayslip._teacher_timetable_attendances:
                        if payslip.employee_id.id == teacher_timetable_attendance['employee_id']:
                            total_weekly_hours += teacher_timetable_attendance['worked_time']
            else:
                # Vérification du temps de l'employé en biométrie
                daily_attendances = self.filter_daily_attendance(date_to, date_from, payslip.employee_id)
                worked_hours = {}
                for daily_attendance in daily_attendances:
                    punching_day = datetime.strftime(daily_attendance.punching_time, DATE_FORMAT)

                    if punching_day not in worked_hours.keys():
                        worked_hours[punching_day] = {}

                    if daily_attendance.punch_type == '0':
                        if '0' not in worked_hours[punching_day].keys():
                            worked_hours[punching_day]['0'] = daily_attendance.punching_time
                    elif daily_attendance.punch_type == '1':
                        worked_hours[punching_day]['1'] = daily_attendance.punching_time

                for daily_attendance in daily_attendances:
                    punching_day = datetime.strftime(daily_attendance.punching_time, DATE_FORMAT)

                    if '0' in worked_hours[punching_day].keys() and '1' in worked_hours[punching_day].keys():
                        worked_hours[punching_day] = worked_hours[punching_day]['1'] - worked_hours[punching_day]['0']
                        worked_hours[punching_day] = timedelta(hours=worked_hours[punching_day].hour, minutes=worked_hours[punching_day].minute)
                        total_weekly_hours += worked_hours[punching_day].total_seconds()
                total_weekly_hours = total_weekly_hours / 3600.0
        total_weekly_hours = round(total_weekly_hours, 2)
        payslip.total_hours = total_weekly_hours

    def run_next_execution(self, machine):
        order = 'id asc'
        next_machines = self.env['biometric.device.details'].sudo().search([('is_active', '=', True)], order=order).sorted(lambda rec: rec.id)
        next_machines = list(next_machines)
        if len(next_machines) > 0:
            next_machine_ids = [next_machine.id for next_machine in next_machines]
            machine_index = next_machine_ids.index(machine.id)
            try:
                next_machine = next_machines[machine_index + 1]
                next_machine.sudo().write({
                    'is_next_execution': True
                })
            except IndexError :
                next_machine = next_machines[0]
                next_machine.sudo().write({
                    'is_next_execution': True
                })
        machine.sudo().write({
            'is_next_execution': False
        })

    @api.model
    def cron_download_attendance(self):
        # machines = self.env['biometric.device.details'].sudo().search([('is_next_execution', '=', True), ('is_active', '=', True)])
        # machines = list(machines)
        # if len(machines) > 0:
        #     for machine in machines:
        machine = self.env['biometric.device.details'].sudo().search([('is_next_execution', '=', True), ('is_active', '=', True)], limit=1)
        if machine:
            try:
                machine.action_download_attendance()
            except UserError as error:
                _logger.info(f'----------- tototototototo UserError {error} -----------')
            except ValidationError as error:
                _logger.info(f'----------- tototototototo ValidationError {error} -----------')
            except Exception as error:
                _logger.info(f'----------- tototototototo Exception {error} -----------')

            self.run_next_execution(machine)
        else:
            machine = self.env['biometric.device.details'].sudo().search([('is_next_execution', '=', False), ('is_active', '=', True)], limit=1)
            if machine:
                try:
                    machine.action_download_attendance()
                except UserError as error:
                    _logger.info(f'----------- tototototototo UserError {error} -----------')
                except ValidationError as error:
                    _logger.info(f'----------- tototototototo ValidationError {error} -----------')
                except Exception as error:
                    _logger.info(f'----------- tototototototo Exception {error} -----------')

                self.run_next_execution(machine)

    def write(self, vals):
        if not self.env.user.has_group('base.user_root') and not self.env.user.has_group('base.user_admin') and self.env.user.id != 2:
            if 'line_ids' not in vals or 'number' not in vals:
                if 'worked_days_line_ids' in vals:
                    if not self.env.user.has_group('om_hr_payroll.group_hr_payroll_perm_write'):
                        raise ValidationError(_("Vous n'êtes pas autorisé à modifier les enregistrements de bulletin de paie (hr.payslip)."))
                    if not self.env.user.has_group('om_hr_payroll.group_hr_payroll_worked_days_perm_write'):
                        raise ValidationError(_("Vous n'êtes pas autorisé à modifier les enregistrements (worked_days) de bulletin de paie (hr.payslip)."))
                else:
                    if not self.env.user.has_group('om_hr_payroll.group_hr_payroll_perm_write'):
                        raise ValidationError(_("Vous n'êtes pas autorisé à modifier les enregistrements de bulletin de paie (hr.payslip)."))

        res = super(HrPayslip, self).write(vals)

        return res

    def copy(self, default=None):
        if not self.env.user.has_group('base.user_root') and not self.env.user.has_group('base.user_admin') and self.env.user.id != 2:
            if not self.env.user.has_group('om_hr_payroll.group_hr_payroll_perm_copy'):
                raise ValidationError(_("Vous n'êtes pas autorisé à dupliquer les enregistrements de bulletin de paie (hr.payslip)."))

        default = dict(default or {})

        res = super(HrPayslip, self).copy(default=default)

        return res

    @api.model
    def create(self, vals):
        payslip_id = super(HrPayslip, self).create(vals)

        date_to = payslip_id.date_to
        date_from = payslip_id.date_from

        if date_to > date.today():
            date_to = date.today()

        if date_from > date_to:
            date_from = date_to

        if payslip_id.employee_id.id:
            if payslip_id.employee_id.is_teacher:
                if payslip_id.employee_id.is_permanent:
                    # Recherche des emplois du temps de l'enseignant pour une période donnée
                    for teacher_timetable_attendance in HrPayslip._teacher_timetable_attendances:
                        if payslip_id.employee_id.id == teacher_timetable_attendance['employee_id']:
                            end_time = teacher_timetable_attendance['worked_end_time']
                            start_time = teacher_timetable_attendance['worked_start_time']
                            datetime_to = datetime.strptime(f"{teacher_timetable_attendance['date']} {end_time}:00", DATETIME_FORMAT)
                            datetime_from = datetime.strptime(f"{teacher_timetable_attendance['date']} {start_time}:00", DATETIME_FORMAT)
                            self.env['hr.payslip.worked_days'].create({
                                'name': '{} {} {}-{}, {}'.format(teacher_timetable_attendance['day_of_week'], datetime.strftime(datetime_from, DATE_FORMAT_FR), datetime.strftime(datetime_from, TIME_FORMAT_FR), datetime.strftime(datetime_to, TIME_FORMAT_FR), teacher_timetable_attendance['subject_name']),
                                'payslip_id': payslip_id.id,
                                'code': payslip_id.code,
                                'number_of_days': 1,
                                'number_of_hours': teacher_timetable_attendance['worked_time'],
                                'contract_id': payslip_id.contract_id.id,
                                'timetable_id': teacher_timetable_attendance['timetable_id'],
                                'date': teacher_timetable_attendance['date'],
                                'start_time': teacher_timetable_attendance['worked_start_time'],
                                'end_time': teacher_timetable_attendance['worked_end_time'],
                                'rate': teacher_timetable_attendance['rate'],
                                'amount': teacher_timetable_attendance['amount'],
                            })
                            teacher_timetable_attendance_id = self.env['teacher.timetable.attendance'].search([('id', '=', teacher_timetable_attendance['id'])], limit=1)
                            if teacher_timetable_attendance_id:
                                teacher_timetable_attendance_id.write({
                                    'is_paid': True,
                                })
                else:
                    # Recherche des emplois du temps de l'enseignant pour une période donnée
                    for teacher_timetable_attendance in HrPayslip._teacher_timetable_attendances:
                        if payslip_id.employee_id.id == teacher_timetable_attendance['employee_id']:
                            end_time = teacher_timetable_attendance['worked_end_time']
                            start_time = teacher_timetable_attendance['worked_start_time']
                            datetime_to = datetime.strptime(f"{teacher_timetable_attendance['date']} {end_time}:00", DATETIME_FORMAT)
                            datetime_from = datetime.strptime(f"{teacher_timetable_attendance['date']} {start_time}:00", DATETIME_FORMAT)
                            self.env['hr.payslip.worked_days'].create({
                                'name': '{} {} {}-{}, {}'.format(teacher_timetable_attendance['day_of_week'], datetime.strftime(datetime_from, DATE_FORMAT_FR), datetime.strftime(datetime_from, TIME_FORMAT_FR), datetime.strftime(datetime_to, TIME_FORMAT_FR), teacher_timetable_attendance['subject_name']),
                                'payslip_id': payslip_id.id,
                                'code': payslip_id.code,
                                'number_of_days': 1,
                                'number_of_hours': teacher_timetable_attendance['worked_time'],
                                'contract_id': payslip_id.contract_id.id,
                                'timetable_id': teacher_timetable_attendance['timetable_id'],
                                'date': teacher_timetable_attendance['date'],
                                'start_time': teacher_timetable_attendance['worked_start_time'],
                                'end_time': teacher_timetable_attendance['worked_end_time'],
                                'rate': teacher_timetable_attendance['rate'],
                                'amount': teacher_timetable_attendance['amount'],
                            })
                            teacher_timetable_attendance_id = self.env['teacher.timetable.attendance'].search([('id', '=', teacher_timetable_attendance['id'])], limit=1)
                            if teacher_timetable_attendance_id:
                                teacher_timetable_attendance_id.write({
                                    'is_paid': True,
                                })
            else:
                # Vérification du temps de l'employé en biométrie
                daily_attendances = self.filter_daily_attendance(date_to, date_from, payslip_id.employee_id)
                worked_hours = {}
                punching_time = {}
                for daily_attendance in daily_attendances:
                    punching_day = datetime.strftime(daily_attendance.punching_time, DATE_FORMAT)

                    if punching_day not in worked_hours.keys():
                        worked_hours[punching_day] = {}

                    if daily_attendance.punch_type == '0':
                        if '0' not in worked_hours[punching_day].keys():
                            worked_hours[punching_day]['0'] = daily_attendance.punching_time
                            punching_time['0'] = daily_attendance.punching_time
                    elif daily_attendance.punch_type == '1':
                        worked_hours[punching_day]['1'] = daily_attendance.punching_time
                        punching_time['1'] = daily_attendance.punching_time

                for daily_attendance in daily_attendances:
                    punching_day = datetime.strftime(daily_attendance.punching_time, DATE_FORMAT)

                    if '0' in worked_hours[punching_day].keys() and '1' in worked_hours[punching_day].keys():
                        worked_hours[punching_day] = worked_hours[punching_day]['1'] - worked_hours[punching_day]['0']
                        worked_hours[punching_day] = timedelta(hours=worked_hours[punching_day].hour, minutes=worked_hours[punching_day].minute)
                        worked_hours[punching_day] = worked_hours[punching_day].total_seconds() / 3600.0
                        worked_hours[punching_day] = round(worked_hours[punching_day], 2)
                        punching_time['0'] = HrPayslip.convert_datetime_from_utc(punching_time['0'])
                        punching_time['1'] = HrPayslip.convert_datetime_from_utc(punching_time['1'])
                        self.env['hr.payslip.worked_days'].create({
                            'name': '{} {} {}'.format(CURRENT_WEEKDAY[str(punching_time['0'].weekday())], datetime.strftime(punching_time['0'], DATETIME_FORMAT_FR), datetime.strftime(punching_time['1'], DATETIME_FORMAT_FR)),
                            'payslip_id': payslip_id.id,
                            'code': payslip_id.code,
                            'number_of_days': 1,
                            'number_of_hours': worked_hours[punching_day],
                            'contract_id': payslip_id.contract_id.id,
                        })

        return payslip_id

    @api.model
    def cron_timetable_presence(self):
        _logger.info(f'+++++++++++ Cron Timetable Presence Executed +++++++++++')

        max_cron_time = self.env['ir.config_parameter'].sudo().get_param(f'siantou.max_cron_time')
        if not max_cron_time:
            max_cron_time = '15'
            self.env['ir.config_parameter'].sudo().set_param(f'siantou.max_cron_time', max_cron_time)
        max_cron_time = int(max_cron_time)

        datetime_from = datetime.now()
        datetime_from = datetime_from + timedelta(hours=1)

        datetime_before = datetime_from - timedelta(minutes=max_cron_time)
        current_date = datetime_before.date()

        time_before = datetime.strftime(datetime_before, TIME_FORMAT_FR)
        time_before = HrPayslip.convert_time_to_float(time_before)

        _logger.info(f'----------- tototototototo current_date {datetime.strftime(current_date, DATE_FORMAT)} -----------')
        _logger.info(f'----------- tototototototo time_before {time_before} -----------')

        # Recherche des emplois du temps de l'enseignant pour une période donnée
        employee_timetables = self.env['siantou.ems.timetable.timetable'].sudo().search([
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
            ('status', 'in', ['pending', 'progress', 'exception']),
        ], order='date asc').filtered(lambda rec: (rec.date < current_date) or (rec.date == current_date and rec.end_time <= time_before))
        employee_timetables = list(employee_timetables)
        for employee_timetable in employee_timetables:
            if employee_timetable.status == 'exception' and employee_timetable.reason not in ['Poinçonnement de début absent ou invalide', 'Poinçonnement de fin absent ou invalide', 'Poinçonnement absent ou invalide', 'Poinçonnement de début et de fin inversé']:
                continue
            if employee_timetable.employee_id.id:
                if employee_timetable.employee_id.is_teacher:
                    # Vérification du temps de cours de l'enseignant en biométrie
                    daily_attendances = self.filter_daily_attendance_teacher(employee_timetable.date, employee_timetable.end_time, employee_timetable.start_time, employee_timetable.employee_id)
                    if len(daily_attendances) == 1:
                        if len(employee_timetable.building_id.device_ids.ids) > 0:
                            if daily_attendances[0].device_id.id not in employee_timetable.building_id.device_ids.ids:
                                if daily_attendances[0].punch_type == '0':
                                    punching_time = daily_attendances[0].punching_time
                                    template = 'om_hr_payroll.om_hr_payroll_template_timetable_notification_device'
                                    punching_time = HrPayslip.convert_datetime_from_utc(punching_time)
                                    message = 'Erreur de poinçonnement de début du {}, {} sur la biométrie {}'.format(CURRENT_WEEKDAY[str(punching_time.weekday())], datetime.strftime(punching_time, DATETIME_FORMAT_FR), daily_attendances[0].device_id.name)
                                    timetable_notifications = self.env['siantou.ems.timetable.notification'].sudo().search([
                                        ('template', '=', template),
                                        ('attendance_id', '=', daily_attendances[0].id),
                                        ('employee_id', '=', daily_attendances[0].employee_id.id),
                                    ])
                                    timetable_notifications = list(timetable_notifications)
                                    if len(timetable_notifications) == 0:
                                        self.env['siantou.ems.timetable.notification'].sudo().create({
                                            'template': template,
                                            'attendance_id': daily_attendances[0].id,
                                            'employee_id': daily_attendances[0].employee_id.id,
                                            'date': date.today(),
                                            'message': message,
                                        })
                                    start_punching_time = daily_attendances[0].punching_time
                                    start_punching_time = UTC_TZ.localize(start_punching_time)
                                    start_time = datetime.strptime(f"{employee_timetable.date} {HrPayslip.convert_float_to_time(employee_timetable.start_time, has_second=True)}", DATETIME_FORMAT)
                                    start_time = HrPayslip.convert_datetime_to_utc(start_time)
                                    if start_punching_time > start_time:
                                        start_time = start_punching_time
                                    start_time = datetime.strftime(start_time, TIME_FORMAT_FR)
                                    start_time = HrPayslip.convert_time_to_float(start_time)
                                    start_time = HrPayslip.increment_float_time(start_time, 1.0)
                                    employee_timetable.sudo().write({
                                        'worked_start_time': start_time,
                                        'worked_end_time': 0.0,
                                        'worked_time': 0.0,
                                        'rate': 0.0,
                                        'amount': 0.0,
                                        'status': 'exception',
                                        'reason': 'Poinçonnement de début sur la biométrie {}'.format(daily_attendances[0].device_id.name),
                                    })
                                    continue
                                elif daily_attendances[0].punch_type == '1':
                                    punching_time = daily_attendances[0].punching_time
                                    template = 'om_hr_payroll.om_hr_payroll_template_timetable_notification_device'
                                    punching_time = HrPayslip.convert_datetime_from_utc(punching_time)
                                    message = 'Erreur de poinçonnement de fin du {}, {} sur la biométrie {}'.format(CURRENT_WEEKDAY[str(punching_time.weekday())], datetime.strftime(punching_time, DATETIME_FORMAT_FR), daily_attendances[0].device_id.name)
                                    timetable_notifications = self.env['siantou.ems.timetable.notification'].sudo().search([
                                        ('template', '=', template),
                                        ('attendance_id', '=', daily_attendances[0].id),
                                        ('employee_id', '=', daily_attendances[0].employee_id.id),
                                    ])
                                    timetable_notifications = list(timetable_notifications)
                                    if len(timetable_notifications) == 0:
                                        self.env['siantou.ems.timetable.notification'].sudo().create({
                                            'template': template,
                                            'attendance_id': daily_attendances[0].id,
                                            'employee_id': daily_attendances[0].employee_id.id,
                                            'date': date.today(),
                                            'message': message,
                                        })
                                    end_punching_time = daily_attendances[0].punching_time
                                    end_punching_time = UTC_TZ.localize(end_punching_time)
                                    end_time = datetime.strptime(f"{employee_timetable.date} {HrPayslip.convert_float_to_time(employee_timetable.end_time, has_second=True)}", DATETIME_FORMAT)
                                    end_time = HrPayslip.convert_datetime_to_utc(end_time)
                                    if end_punching_time < end_time:
                                        end_time = end_punching_time
                                    end_time = datetime.strftime(end_time, TIME_FORMAT_FR)
                                    end_time = HrPayslip.convert_time_to_float(end_time)
                                    end_time = HrPayslip.increment_float_time(end_time, 1.0)
                                    employee_timetable.sudo().write({
                                        'worked_start_time': 0.0,
                                        'worked_end_time': end_time,
                                        'worked_time': 0.0,
                                        'rate': 0.0,
                                        'amount': 0.0,
                                        'status': 'exception',
                                        'reason': 'Poinçonnement de fin sur la biométrie {}'.format(daily_attendances[0].device_id.name),
                                    })
                                    continue
                                else:
                                    punching_time = daily_attendances[0].punching_time
                                    template = 'om_hr_payroll.om_hr_payroll_template_timetable_notification_device'
                                    punching_time = HrPayslip.convert_datetime_from_utc(punching_time)
                                    message = 'Erreur de poinçonnement de début ou de fin du {}, {} sur la biométrie {}'.format(CURRENT_WEEKDAY[str(punching_time.weekday())], datetime.strftime(punching_time, DATETIME_FORMAT_FR), daily_attendances[0].device_id.name)
                                    timetable_notifications = self.env['siantou.ems.timetable.notification'].sudo().search([
                                        ('template', '=', template),
                                        ('attendance_id', '=', daily_attendances[0].id),
                                        ('employee_id', '=', daily_attendances[0].employee_id.id),
                                    ])
                                    timetable_notifications = list(timetable_notifications)
                                    if len(timetable_notifications) == 0:
                                        self.env['siantou.ems.timetable.notification'].sudo().create({
                                            'template': template,
                                            'attendance_id': daily_attendances[0].id,
                                            'employee_id': daily_attendances[0].employee_id.id,
                                            'date': date.today(),
                                            'message': message,
                                        })
                                    employee_timetable.sudo().write({
                                        'worked_start_time': 0.0,
                                        'worked_end_time': 0.0,
                                        'worked_time': 0.0,
                                        'rate': 0.0,
                                        'amount': 0.0,
                                        'status': 'exception',
                                        'reason': 'Poinçonnement de début ou de fin sur la biométrie {}'.format(daily_attendances[0].device_id.name),
                                    })
                                    continue
                        if daily_attendances[0].punch_type == '0':
                            start_punching_time = daily_attendances[0].punching_time
                            start_punching_time = UTC_TZ.localize(start_punching_time)
                            start_time = datetime.strptime(f"{employee_timetable.date} {HrPayslip.convert_float_to_time(employee_timetable.start_time, has_second=True)}", DATETIME_FORMAT)
                            start_time = HrPayslip.convert_datetime_to_utc(start_time)
                            if start_punching_time > start_time:
                                start_time = start_punching_time
                            start_time = datetime.strftime(start_time, TIME_FORMAT_FR)
                            start_time = HrPayslip.convert_time_to_float(start_time)
                            start_time = HrPayslip.increment_float_time(start_time, 1.0)
                            employee_timetable.sudo().write({
                                'worked_start_time': start_time,
                                'worked_end_time': 0.0,
                                'worked_time': 0.0,
                                'rate': 0.0,
                                'amount': 0.0,
                                'status': 'exception',
                                'reason': 'Poinçonnement de fin absent ou invalide',
                            })
                        elif daily_attendances[0].punch_type == '1':
                            end_punching_time = daily_attendances[0].punching_time
                            end_punching_time = UTC_TZ.localize(end_punching_time)
                            end_time = datetime.strptime(f"{employee_timetable.date} {HrPayslip.convert_float_to_time(employee_timetable.end_time, has_second=True)}", DATETIME_FORMAT)
                            end_time = HrPayslip.convert_datetime_to_utc(end_time)
                            if end_punching_time < end_time:
                                end_time = end_punching_time
                            end_time = datetime.strftime(end_time, TIME_FORMAT_FR)
                            end_time = HrPayslip.convert_time_to_float(end_time)
                            end_time = HrPayslip.increment_float_time(end_time, 1.0)
                            employee_timetable.sudo().write({
                                'worked_start_time': 0.0,
                                'worked_end_time': end_time,
                                'worked_time': 0.0,
                                'rate': 0.0,
                                'amount': 0.0,
                                'status': 'exception',
                                'reason': 'Poinçonnement de début absent ou invalide',
                            })
                        else:
                            employee_timetable.sudo().write({
                                'worked_start_time': 0.0,
                                'worked_end_time': 0.0,
                                'worked_time': 0.0,
                                'rate': 0.0,
                                'amount': 0.0,
                                'status': 'exception',
                                'reason': 'Poinçonnement absent ou invalide',
                            })
                    elif len(daily_attendances) > 1:
                        if len(employee_timetable.building_id.device_ids.ids) > 0:
                            if daily_attendances[1].device_id.id not in employee_timetable.building_id.device_ids.ids:
                                punching_time = daily_attendances[1].punching_time
                                template = 'om_hr_payroll.om_hr_payroll_template_timetable_notification_device'
                                punching_time = HrPayslip.convert_datetime_from_utc(punching_time)
                                message = 'Erreur de poinçonnement de fin du {}, {} sur la biométrie {}'.format(CURRENT_WEEKDAY[str(punching_time.weekday())], datetime.strftime(punching_time, DATETIME_FORMAT_FR), daily_attendances[1].device_id.name)
                                timetable_notifications = self.env['siantou.ems.timetable.notification'].sudo().search([
                                    ('template', '=', template),
                                    ('attendance_id', '=', daily_attendances[1].id),
                                    ('employee_id', '=', daily_attendances[1].employee_id.id),
                                ])
                                timetable_notifications = list(timetable_notifications)
                                if len(timetable_notifications) == 0:
                                    self.env['siantou.ems.timetable.notification'].sudo().create({
                                        'template': template,
                                        'attendance_id': daily_attendances[1].id,
                                        'employee_id': daily_attendances[1].employee_id.id,
                                        'date': date.today(),
                                        'message': message,
                                    })
                                    end_punching_time = daily_attendances[1].punching_time
                                    end_punching_time = UTC_TZ.localize(end_punching_time)
                                    end_time = datetime.strptime(f"{employee_timetable.date} {HrPayslip.convert_float_to_time(employee_timetable.end_time, has_second=True)}", DATETIME_FORMAT)
                                    end_time = HrPayslip.convert_datetime_to_utc(end_time)
                                    if end_punching_time < end_time:
                                        end_time = end_punching_time
                                    end_time = datetime.strftime(end_time, TIME_FORMAT_FR)
                                    end_time = HrPayslip.convert_time_to_float(end_time)
                                    end_time = HrPayslip.increment_float_time(end_time, 1.0)
                                    employee_timetable.sudo().write({
                                        'worked_start_time': 0.0,
                                        'worked_end_time': end_time,
                                        'worked_time': 0.0,
                                        'rate': 0.0,
                                        'amount': 0.0,
                                        'status': 'exception',
                                        'reason': 'Poinçonnement de fin sur la biométrie {}'.format(daily_attendances[1].device_id.name),
                                    })
                                    continue
                            if daily_attendances[0].device_id.id not in employee_timetable.building_id.device_ids.ids:
                                punching_time = daily_attendances[0].punching_time
                                template = 'om_hr_payroll.om_hr_payroll_template_timetable_notification_device'
                                punching_time = HrPayslip.convert_datetime_from_utc(punching_time)
                                message = 'Erreur de poinçonnement de début du {}, {} sur la biométrie {}'.format(CURRENT_WEEKDAY[str(punching_time.weekday())], datetime.strftime(punching_time, DATETIME_FORMAT_FR), daily_attendances[0].device_id.name)
                                timetable_notifications = self.env['siantou.ems.timetable.notification'].sudo().search([
                                    ('template', '=', template),
                                    ('attendance_id', '=', daily_attendances[0].id),
                                    ('employee_id', '=', daily_attendances[0].employee_id.id),
                                ])
                                timetable_notifications = list(timetable_notifications)
                                if len(timetable_notifications) == 0:
                                    self.env['siantou.ems.timetable.notification'].sudo().create({
                                        'template': template,
                                        'attendance_id': daily_attendances[0].id,
                                        'employee_id': daily_attendances[0].employee_id.id,
                                        'date': date.today(),
                                        'message': message,
                                    })
                                    start_punching_time = daily_attendances[0].punching_time
                                    start_punching_time = UTC_TZ.localize(start_punching_time)
                                    start_time = datetime.strptime(f"{employee_timetable.date} {HrPayslip.convert_float_to_time(employee_timetable.start_time, has_second=True)}", DATETIME_FORMAT)
                                    start_time = HrPayslip.convert_datetime_to_utc(start_time)
                                    if start_punching_time > start_time:
                                        start_time = start_punching_time
                                    start_time = datetime.strftime(start_time, TIME_FORMAT_FR)
                                    start_time = HrPayslip.convert_time_to_float(start_time)
                                    start_time = HrPayslip.increment_float_time(start_time, 1.0)
                                    employee_timetable.sudo().write({
                                        'worked_start_time': start_time,
                                        'worked_end_time': 0.0,
                                        'worked_time': 0.0,
                                        'rate': 0.0,
                                        'amount': 0.0,
                                        'status': 'exception',
                                        'reason': 'Poinçonnement de début sur la biométrie {}'.format(daily_attendances[0].device_id.name),
                                    })
                                    continue
                        end_punching_time = daily_attendances[1].punching_time
                        start_punching_time = daily_attendances[0].punching_time
                        end_punching_time = UTC_TZ.localize(end_punching_time)
                        start_punching_time = UTC_TZ.localize(start_punching_time)
                        end_time = datetime.strptime(f"{employee_timetable.date} {HrPayslip.convert_float_to_time(employee_timetable.end_time, has_second=True)}", DATETIME_FORMAT)
                        start_time = datetime.strptime(f"{employee_timetable.date} {HrPayslip.convert_float_to_time(employee_timetable.start_time, has_second=True)}", DATETIME_FORMAT)
                        end_time = HrPayslip.convert_datetime_to_utc(end_time)
                        start_time = HrPayslip.convert_datetime_to_utc(start_time)
                        if end_punching_time < end_time:
                            end_time = end_punching_time
                        if start_punching_time > start_time:
                            start_time = start_punching_time
                        if start_time > end_time:
                            end_time = datetime.strftime(end_time, TIME_FORMAT_FR)
                            start_time = datetime.strftime(start_time, TIME_FORMAT_FR)
                            end_time = HrPayslip.convert_time_to_float(end_time)
                            start_time = HrPayslip.convert_time_to_float(start_time)
                            end_time = HrPayslip.increment_float_time(end_time, 1.0)
                            start_time = HrPayslip.increment_float_time(start_time, 1.0)
                            employee_timetable.sudo().write({
                                'worked_start_time': start_time,
                                'worked_end_time': end_time,
                                'worked_time': 0.0,
                                'rate': 0.0,
                                'amount': 0.0,
                                'status': 'exception',
                                'reason': 'Poinçonnement de début et de fin inversé',
                            })
                        else:
                            end_time = datetime.strftime(end_time, TIME_FORMAT_FR)
                            start_time = datetime.strftime(start_time, TIME_FORMAT_FR)
                            end_time = HrPayslip.convert_time_to_float(end_time)
                            start_time = HrPayslip.convert_time_to_float(start_time)
                            end_time = HrPayslip.increment_float_time(end_time, 1.0)
                            start_time = HrPayslip.increment_float_time(start_time, 1.0)
                            employee_timetable.sudo().write({
                                'worked_start_time': start_time,
                                'worked_end_time': end_time,
                                'worked_time': 0.0,
                                'rate': 0.0,
                                'amount': 0.0,
                                'status': 'present',
                                'reason': None,
                            })
                    else:
                        template = 'om_hr_payroll.om_hr_payroll_template_timetable_notification_absence'
                        end_time = datetime.strptime(f"{employee_timetable.date} {HrPayslip.convert_float_to_time(employee_timetable.end_time, has_second=True)}", DATETIME_FORMAT)
                        start_time = datetime.strptime(f"{employee_timetable.date} {HrPayslip.convert_float_to_time(employee_timetable.start_time, has_second=True)}", DATETIME_FORMAT)
                        end_time = datetime.strftime(end_time, TIME_FORMAT_FR)
                        start_time = datetime.strftime(start_time, TIME_FORMAT_FR)
                        message = 'Absence du {}, {} {}-{}'.format(CURRENT_WEEKDAY[str(employee_timetable.date.weekday())], datetime.strftime(employee_timetable.date, DATE_FORMAT_FR), start_time, end_time)
                        timetable_notifications = self.env['siantou.ems.timetable.notification'].sudo().search([
                            ('template', '=', template),
                            ('timetable_id', '=', employee_timetable.id),
                            ('employee_id', '=', employee_timetable.employee_id.id),
                        ])
                        timetable_notifications = list(timetable_notifications)
                        if len(timetable_notifications) == 0:
                            self.env['siantou.ems.timetable.notification'].sudo().create({
                                'template': template,
                                'timetable_id': employee_timetable.id,
                                'employee_id': employee_timetable.employee_id.id,
                                'date': date.today(),
                                'message': message,
                            })
                        employee_timetable.sudo().write({
                            'worked_start_time': 0.0,
                            'worked_end_time': 0.0,
                            'worked_time': 0.0,
                            'rate': 0.0,
                            'amount': 0.0,
                            'status': 'absent',
                            'reason': None,
                        })
            else:
                employee_timetable.sudo().write({
                    'worked_start_time': 0.0,
                    'worked_end_time': 0.0,
                    'worked_time': 0.0,
                    'rate': 0.0,
                    'amount': 0.0,
                    'status': 'absent',
                    'reason': None,
                })

    @api.model
    def cron_timetable_rappel(self):
        _logger.info(f'+++++++++++ Cron Timetable Rappel Executed +++++++++++')

        max_cron_time = self.env['ir.config_parameter'].sudo().get_param(f'siantou.max_cron_time')
        if not max_cron_time:
            max_cron_time = '15'
            self.env['ir.config_parameter'].sudo().set_param(f'siantou.max_cron_time', max_cron_time)
        max_cron_time = int(max_cron_time)

        datetime_from = datetime.now()
        datetime_from = datetime_from + timedelta(days=1, hours=1)

        datetime_before = datetime_from - timedelta(minutes=max_cron_time)
        current_date = datetime_before.date()

        time_before = datetime.strftime(datetime_before, TIME_FORMAT_FR)
        time_before = HrPayslip.convert_time_to_float(time_before)

        _logger.info(f'----------- tototototototo current_date {datetime.strftime(current_date, DATE_FORMAT)} -----------')
        _logger.info(f'----------- tototototototo time_before {time_before} -----------')

        # Recherche des emplois du temps de l'enseignant pour une période donnée
        employee_timetables = self.env['siantou.ems.timetable.timetable'].sudo().search([
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
            ('status', '=', 'pending'),
        ], order='date asc').filtered(lambda rec: rec.date and rec.day_of_week and rec.date == current_date and rec.start_time <= time_before and rec.end_time >= time_before)
        employee_timetables = list(employee_timetables)
        for employee_timetable in employee_timetables:
            if employee_timetable.employee_id.id:
                if employee_timetable.employee_id.is_teacher:
                    template = 'om_hr_payroll.om_hr_payroll_template_timetable_notification_rappel'
                    end_time = datetime.strptime(f"{employee_timetable.date} {HrPayslip.convert_float_to_time(employee_timetable.end_time, has_second=True)}", DATETIME_FORMAT)
                    start_time = datetime.strptime(f"{employee_timetable.date} {HrPayslip.convert_float_to_time(employee_timetable.start_time, has_second=True)}", DATETIME_FORMAT)
                    end_time = datetime.strftime(end_time, TIME_FORMAT_FR)
                    start_time = datetime.strftime(start_time, TIME_FORMAT_FR)
                    message = 'Rappel du {}, {} {} {}'.format(CURRENT_WEEKDAY[str(employee_timetable.date.weekday())], datetime.strftime(employee_timetable.date, DATE_FORMAT_FR), start_time, end_time)
                    timetable_notifications = self.env['siantou.ems.timetable.notification'].sudo().search([
                        ('template', '=', template),
                        ('timetable_id', '=', employee_timetable.id),
                        ('employee_id', '=', employee_timetable.employee_id.id),
                    ])
                    timetable_notifications = list(timetable_notifications)
                    if len(timetable_notifications) == 0:
                        self.env['siantou.ems.timetable.notification'].sudo().create({
                            'template': template,
                            'timetable_id': employee_timetable.id,
                            'employee_id': employee_timetable.employee_id.id,
                            'date': date.today(),
                            'message': message,
                        })

    @api.model
    def cron_timetable_retard(self):
        _logger.info(f'+++++++++++ Cron Timetable Retard Executed +++++++++++')

        max_cron_time = self.env['ir.config_parameter'].sudo().get_param(f'siantou.max_cron_time')
        if not max_cron_time:
            max_cron_time = '15'
            self.env['ir.config_parameter'].sudo().set_param(f'siantou.max_cron_time', max_cron_time)
        max_cron_time = int(max_cron_time)

        datetime_from = datetime.now()
        datetime_from = datetime_from + timedelta(hours=1)

        datetime_before = datetime_from - timedelta(minutes=max_cron_time)
        current_date = datetime_before.date()

        time_before = datetime.strftime(datetime_before, TIME_FORMAT_FR)
        time_before = HrPayslip.convert_time_to_float(time_before)

        _logger.info(f'----------- tototototototo current_date {datetime.strftime(current_date, DATE_FORMAT)} -----------')
        _logger.info(f'----------- tototototototo time_before {time_before} -----------')

        # Recherche des emplois du temps de l'enseignant pour une période donnée
        employee_timetables = self.env['siantou.ems.timetable.timetable'].sudo().search([
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
            ('status', '=', 'pending'),
        ], order='date asc').filtered(lambda rec: rec.date and rec.day_of_week and rec.date == current_date and rec.start_time <= time_before and rec.end_time >= time_before)
        employee_timetables = list(employee_timetables)
        for employee_timetable in employee_timetables:
            if employee_timetable.employee_id.id:
                if employee_timetable.employee_id.is_teacher:
                    # Vérification du temps de cours de l'enseignant en biométrie
                    daily_attendances = self.filter_daily_attendance_teacher(employee_timetable.date, employee_timetable.end_time, employee_timetable.start_time, employee_timetable.employee_id)
                    if len(daily_attendances) == 0:
                        template = 'om_hr_payroll.om_hr_payroll_template_timetable_notification_retard'
                        end_time = datetime.strptime(f"{employee_timetable.date} {HrPayslip.convert_float_to_time(employee_timetable.end_time, has_second=True)}", DATETIME_FORMAT)
                        start_time = datetime.strptime(f"{employee_timetable.date} {HrPayslip.convert_float_to_time(employee_timetable.start_time, has_second=True)}", DATETIME_FORMAT)
                        end_time = datetime.strftime(end_time, TIME_FORMAT_FR)
                        start_time = datetime.strftime(start_time, TIME_FORMAT_FR)
                        message = 'Retard du {}, {} {} {}'.format(CURRENT_WEEKDAY[str(employee_timetable.date.weekday())], datetime.strftime(employee_timetable.date, DATE_FORMAT_FR), start_time, end_time)
                        timetable_notifications = self.env['siantou.ems.timetable.notification'].sudo().search([
                            ('template', '=', template),
                            ('timetable_id', '=', employee_timetable.id),
                            ('employee_id', '=', employee_timetable.employee_id.id),
                        ])
                        timetable_notifications = list(timetable_notifications)
                        if len(timetable_notifications) == 0:
                            self.env['siantou.ems.timetable.notification'].sudo().create({
                                'template': template,
                                'timetable_id': employee_timetable.id,
                                'employee_id': employee_timetable.employee_id.id,
                                'date': date.today(),
                                'message': message,
                            })

    def search_filtered_daily_attendance_teacher(self, rec, punching_time):
        min_start_time = self.env['ir.config_parameter'].sudo().get_param(f'siantou.min_start_time')
        if not min_start_time:
            min_start_time = '30'
            self.env['ir.config_parameter'].sudo().set_param(f'siantou.min_start_time', min_start_time)
        max_end_time = self.env['ir.config_parameter'].sudo().get_param(f'siantou.max_end_time')
        if not max_end_time:
            max_end_time = '15'
            self.env['ir.config_parameter'].sudo().set_param(f'siantou.max_end_time', max_end_time)
        min_start_time = int(min_start_time)
        max_end_time = int(max_end_time)
        # Filtre des données biométriques de l'enseignant pour une période donnée
        current_date = datetime.strftime(rec.date, DATE_FORMAT)

        end_time = HrPayslip.convert_float_to_time(rec.end_time, has_second=True)
        start_time = HrPayslip.convert_float_to_time(rec.start_time, has_second=True)

        datetime_to = datetime.strptime(f"{current_date} {end_time}", DATETIME_FORMAT)
        datetime_from = datetime.strptime(f"{current_date} {start_time}", DATETIME_FORMAT)

        datetime_before = datetime_from - timedelta(minutes=min_start_time)
        # datetime_from = datetime_from + timedelta(minutes=max_end_time)

        datetime_after = datetime_to + timedelta(minutes=max_end_time)
        # datetime_to = datetime_to - timedelta(minutes=max_end_time)

        datetime_before = HrPayslip.convert_datetime_to_utc(datetime_before)
        datetime_from = HrPayslip.convert_datetime_to_utc(datetime_from)
        datetime_after = HrPayslip.convert_datetime_to_utc(datetime_after)
        datetime_to = HrPayslip.convert_datetime_to_utc(datetime_to)

        result = (UTC_TZ.localize(punching_time) >= datetime_before and UTC_TZ.localize(punching_time) <= datetime_after)
        return result

    @api.model
    def cron_timetable_exception(self):
        _logger.info(f'+++++++++++ Cron Timetable Exception Executed +++++++++++')

        max_cron_time = self.env['ir.config_parameter'].sudo().get_param(f'siantou.max_cron_time')
        if not max_cron_time:
            max_cron_time = '15'
            self.env['ir.config_parameter'].sudo().set_param(f'siantou.max_cron_time', max_cron_time)
        max_cron_time = int(max_cron_time)

        datetime_from = datetime.now()
        datetime_from = datetime_from + timedelta(hours=1)
        current_date = datetime_from.date()

        datetime_before = datetime_from - timedelta(minutes=max_cron_time)

        _logger.info(f'----------- tototototototo datetime_from {datetime.strftime(datetime_from, DATETIME_FORMAT)} -----------')
        _logger.info(f'----------- tototototototo datetime_before {datetime.strftime(datetime_before, DATETIME_FORMAT)} -----------')

        datetime_before = HrPayslip.convert_datetime_to_utc(datetime_before)
        datetime_from = HrPayslip.convert_datetime_to_utc(datetime_from)

        daily_attendances = self.env['daily.attendance'].sudo().search([
            ('punch_type', 'in', ['0', '1', '255'])
        ], order='punching_time asc').filtered(lambda rec: UTC_TZ.localize(rec.punching_time) >= datetime_before and UTC_TZ.localize(rec.punching_time) <= datetime_from).sorted(lambda rec: UTC_TZ.localize(rec.punching_time))
        daily_attendances = list(daily_attendances)
        for daily_attendance in daily_attendances:
            punching_time = daily_attendance.punching_time

            if daily_attendance.employee_id.id:
                if daily_attendance.employee_id.is_teacher:
                    # employee_timetables = self.env['siantou.ems.timetable.timetable'].sudo().search([
                    #     '|',
                    #     '&',
                    #     ('group_id.is_active', '=', True),
                    #     ('group_id.is_submit', '=', False),
                    #     '&',
                    #     ('group_parent_id.is_active', '=', True),
                    #     ('group_parent_id.is_submit', '=', False),
                    #     ('employee_id', '=', daily_attendance.employee_id.id),
                    #     ('status', '=', 'pending'),
                    # ], order='date asc').filtered(lambda rec: (UTC_TZ.localize(punching_time) >= HrPayslip.convert_datetime_to_utc(datetime.strptime(f"{rec.date} {HrPayslip.convert_float_to_time(rec.start_time)}', DATETIME_FORMAT) - timedelta(minutes=15)) and UTC_TZ.localize(punching_time) <= HrPayslip.convert_datetime_to_utc(datetime.strptime(f'{rec.date} {HrPayslip.convert_float_to_time(rec.start_time)}', DATETIME_FORMAT) + timedelta(minutes=15))) or (UTC_TZ.localize(punching_time) >= HrPayslip.convert_datetime_to_utc(datetime.strptime(f'{rec.date} {HrPayslip.convert_float_to_time(rec.end_time)}', DATETIME_FORMAT)) and UTC_TZ.localize(punching_time) <= HrPayslip.convert_datetime_to_utc(datetime.strptime(f'{rec.date} {HrPayslip.convert_float_to_time(rec.end_time)}", DATETIME_FORMAT) + timedelta(minutes=15))), has_second=True)
                    employee_timetables = self.env['siantou.ems.timetable.timetable'].sudo().search([
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
                        ('employee_id', '=', daily_attendance.employee_id.id),
                        ('status', 'in', ['pending', 'progress']),
                    ], order='date asc').filtered(lambda rec: self.search_filtered_daily_attendance_teacher(rec, punching_time))
                    employee_timetables = list(employee_timetables)
                    if len(employee_timetables) > 0:
                        for employee_timetable in employee_timetables:
                            employee_timetable.sudo().write({'status': 'progress', 'reason': None})
                    else:
                        template = 'om_hr_payroll.om_hr_payroll_template_timetable_notification_exception'
                        punching_time = HrPayslip.convert_datetime_from_utc(punching_time)
                        message = 'Exception du {}, {} sur la biométrie {}'.format(CURRENT_WEEKDAY[str(punching_time.weekday())], datetime.strftime(punching_time, DATETIME_FORMAT_FR), daily_attendance.device_id.name)
                        timetable_notifications = self.env['siantou.ems.timetable.notification'].sudo().search([
                            ('template', '=', template),
                            ('attendance_id', '=', daily_attendance.id),
                            ('employee_id', '=', daily_attendance.employee_id.id),
                        ])
                        timetable_notifications = list(timetable_notifications)
                        if len(timetable_notifications) == 0:
                            self.env['siantou.ems.timetable.notification'].sudo().create({
                                'template': template,
                                'attendance_id': daily_attendance.id,
                                'employee_id': daily_attendance.employee_id.id,
                                'date': date.today(),
                                'message': message,
                            })

    @api.model
    def cron_timetable_reset(self):
        _logger.info(f'+++++++++++ Cron Timetable Reset Executed +++++++++++')

        datetime_from = datetime.now()

        current_date = datetime_from.date()

        _logger.info(f'----------- tototototototo current_date {datetime.strftime(current_date, DATE_FORMAT)} -----------')

        # Recherche des emplois du temps de l'enseignant pour une période donnée
        employee_timetables = self.env['siantou.ems.timetable.timetable'].sudo().search([
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
            ('status', 'in', ['present', 'progress', 'absent']),
        ], order='date asc').filtered(lambda rec: rec.date and rec.day_of_week and rec.date == current_date)
        employee_timetables = list(employee_timetables)
        for employee_timetable in employee_timetables:
            employee_timetable.sudo().write({
                'worked_start_time': 0.0,
                'worked_end_time': 0.0,
                'worked_time': 0.0,
                'rate': 0.0,
                'amount': 0.0,
                'status': 'pending',
                'reason': None,
            })

    @api.depends('employee_id', 'date_to', 'date_from')
    def _compute_total_hours(self):
        for payslip in self:
            self.employee_total_hours(payslip)

    @api.onchange('employee_id', 'date_to', 'date_from')
    def onchange_employee_total_hours(self):
        for payslip in self:
            self.employee_total_hours(payslip)

    def _compute_details_by_salary_rule_category(self):
        for payslip in self:
            payslip.details_by_salary_rule_category = payslip.mapped('line_ids').filtered(lambda line: line.category_id)

    def _compute_payslip_count(self):
        for payslip in self:
            payslip.payslip_count = len(payslip.line_ids)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        if any(self.filtered(lambda payslip: payslip.date_from > payslip.date_to)):
            raise ValidationError(_("Payslip 'Date From' must be earlier 'Date To'."))

    def action_payslip_draft(self):
        return self.write({'state': 'draft'})

    def action_payslip_done(self):
        self.compute_sheet()
        return self.write({'state': 'done'})

    def action_payslip_cancel(self):
        # if self.filtered(lambda slip: slip.state == 'done'):
        #     raise UserError(_('Cannot cancel a payslip that is done'))
        return self.write({'state': 'cancel'})

    def action_payslip_all_draft(self):
        active_ids = self.env.context.get('active_ids', [])
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')
        payslips = self.env['hr.payslip'].search([
            ('id', 'in', active_ids),
            ('state', '=', 'cancel'),
        ])
        for payslip in payslips:
            payslip.action_payslip_draft()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_payslip_all_done(self):
        active_ids = self.env.context.get('active_ids', [])
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')
        payslips = self.env['hr.payslip'].search([
            ('id', 'in', active_ids),
            ('state', '=', 'draft'),
        ])
        for payslip in payslips:
            payslip.action_payslip_done()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_payslip_all_cancel(self):
        active_ids = self.env.context.get('active_ids', [])
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')
        payslips = self.env['hr.payslip'].search([
            ('id', 'in', active_ids),
            ('state', 'in', ['draft', 'verify', 'done']),
        ])
        for payslip in payslips:
            payslip.action_payslip_cancel()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def refund_sheet(self):
        for payslip in self:
            copied_payslip = payslip.copy({'credit_note': True, 'name': _('Refund: ') + payslip.name})
            copied_payslip.compute_sheet()
            copied_payslip.action_payslip_done()
        form_view_ref = self.env.ref('om_om_hr_payroll.view_hr_payslip_form', False)
        tree_view_ref = self.env.ref('om_om_hr_payroll.view_hr_payslip_tree', False)
        return {
            'name': (_("Refund Payslip")),
            'view_mode': 'tree, form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'hr.payslip',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': "[('id', 'in', %s)]" % copied_payslip.ids,
            'views': [(tree_view_ref and tree_view_ref.id or False, 'tree'), (form_view_ref and form_view_ref.id or False, 'form')],
            'context': {}
        }

    def action_send_email(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = self.env.ref('om_hr_payroll.mail_template_payslip').id
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data._xmlid_lookup('mail.email_compose_message_wizard_form')[1]

        except ValueError:
            compose_form_id = False
        ctx = {
            'default_model': 'hr.payslip',
            'default_res_ids': self.ids,
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
        }
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def check_done(self):
        return True

    def unlink(self):
        if not self.env.user.has_group('base.user_root') and not self.env.user.has_group('base.user_admin') and self.env.user.id != 2:
            if not self.env.user.has_group('om_hr_payroll.group_hr_payroll_perm_unlink'):
                raise ValidationError(_("Vous n'êtes pas autorisé à supprimer les enregistrements de bulletin de paie (hr.payslip)."))

        if any(self.filtered(lambda payslip: payslip.state not in ('draft', 'cancel'))):
            raise UserError(_('You cannot delete a payslip which is not draft or cancelled!'))

        res = super(HrPayslip, self).unlink()

        return res

    # TODO move this function into hr_contract module, on hr.employee object
    @api.model
    def get_contract(self, employee, date_from, date_to):
        """
        @param employee: recordset of employee
        @param date_from: date field
        @param date_to: date field
        @return: returns the ids of all the contracts for the given employee that need to be considered for the given dates
        """
        # a contract is valid if it ends between the given dates
        clause_1 = ['&', ('date_end', '<=', date_to), ('date_end', '>=', date_from)]
        # OR if it starts between the given dates
        clause_2 = ['&', ('date_start', '<=', date_to), ('date_start', '>=', date_from)]
        # OR if it starts before the date_from and finish after the date_end (or never finish)
        clause_3 = ['&', ('date_start', '<=', date_from), '|', ('date_end', '=', False), ('date_end', '>=', date_to)]
        clause_final = [('employee_id', '=', employee.id), ('state', '=', 'open'), '|', '|'] + clause_1 + clause_2 + clause_3
        return self.env['hr.contract'].search(clause_final).ids

    def compute_sheet(self):
        for payslip in self:
            number = payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')
            # delete old payslip lines
            payslip.line_ids.unlink()
            # set the list of contract for which the rules have to be applied
            # if we don't give the contract, then the rules to apply should be for all current contracts of the employee
            contract_ids = payslip.contract_id.ids or \
                self.get_contract(payslip.employee_id, payslip.date_from, payslip.date_to)
            if not contract_ids:
                raise ValidationError(_("No running contract found for the employee: %s or no contract in the given period" % payslip.employee_id.name))
            lines = [(0, 0, line) for line in self._get_payslip_lines(contract_ids, payslip.id)]
            payslip.write({'line_ids': lines, 'number': number})
        return True

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        @param contract: Browse record of contracts
        @return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
        """
        res = []
        # fill only if the contract as a working schedule linked
        for contract in contracts.filtered(lambda contract: contract.resource_calendar_id):
            day_from = datetime.combine(fields.Date.from_string(date_from), time.min)
            day_to = datetime.combine(fields.Date.from_string(date_to), time.max)

            # compute leave days
            leaves = {}
            calendar = contract.resource_calendar_id
            tz = pytz.timezone(calendar.tz)
            day_leave_intervals = contract.employee_id.list_leaves(day_from, day_to, calendar=contract.resource_calendar_id)
            for day, hours, leave in day_leave_intervals:
                holiday = leave.holiday_id
                current_leave_struct = leaves.setdefault(holiday.holiday_status_id, {
                    'name': holiday.holiday_status_id.name or _('Global Leaves'),
                    'sequence': 5,
                    'code': holiday.holiday_status_id.code or 'GLOBAL',
                    'number_of_days': 0.0,
                    'number_of_hours': 0.0,
                    'contract_id': contract.id,
                })
                current_leave_struct['number_of_hours'] -= hours
                work_hours = calendar.get_work_hours_count(
                    tz.localize(datetime.combine(day, time.min)),
                    tz.localize(datetime.combine(day, time.max)),
                    compute_leaves=False,
                )
                if work_hours:
                    current_leave_struct['number_of_days'] -= hours / work_hours

            # compute worked days
            work_data = contract.employee_id._get_work_days_data(
                day_from,
                day_to,
                calendar=contract.resource_calendar_id,
                compute_leaves=False,
            )
            attendances = {
                'name': _("Normal Working Days paid at 100%"),
                'sequence': 1,
                'code': 'WORK100',
                'number_of_days': work_data['days'],
                'number_of_hours': work_data['hours'],
                'contract_id': contract.id,
            }

            res.append(attendances)
            res.extend(leaves.values())
        return res

    @api.model
    def get_inputs(self, contracts, date_from, date_to):
        res = []

        structure_ids = contracts.get_all_structures()
        rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x:x[1])]
        inputs = self.env['hr.salary.rule'].browse(sorted_rule_ids).mapped('input_ids')

        for contract in contracts:
            for input in inputs:
                input_data = {
                    'name': input.name,
                    'code': input.code,
                    'contract_id': contract.id,
                }
                res += [input_data]
        return res

    @api.model
    def _get_payslip_lines(self, contract_ids, payslip_id):
        def _sum_salary_rule_category(localdict, category, amount):
            if category.parent_id:
                localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)
            localdict['categories'].dict[category.code] = category.code in localdict['categories'].dict and localdict['categories'].dict[category.code] + amount or amount
            return localdict

        class BrowsableObject(object):
            def __init__(self, employee_id, dict, env):
                self.employee_id = employee_id
                self.dict = dict
                self.env = env

            def __getattr__(self, attr):
                return attr in self.dict and self.dict.__getitem__(attr) or 0.0

        class InputLine(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""
            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(amount) as sum
                    FROM hr_payslip as hp, hr_payslip_input as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                    (self.employee_id, from_date, to_date, code))
                return self.env.cr.fetchone()[0] or 0.0

        class WorkedDays(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""
            def _sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(number_of_days) as number_of_days, sum(number_of_hours) as number_of_hours
                    FROM hr_payslip as hp, hr_payslip_worked_days as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                    (self.employee_id, from_date, to_date, code))
                return self.env.cr.fetchone()

            def sum(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            def sum_hours(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0

        class Payslips(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""SELECT sum(case when hp.credit_note = False then (pl.total) else (-pl.total) end)
                            FROM hr_payslip as hp, hr_payslip_line as pl
                            WHERE hp.employee_id = %s AND hp.state = 'done'
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pl.slip_id AND pl.code = %s""",
                            (self.employee_id, from_date, to_date, code))
                res = self.env.cr.fetchone()
                return res and res[0] or 0.0

        #we keep a dict with the result because a value can be overwritten by another rule with the same code
        result_dict = {}
        rules_dict = {}
        worked_days_dict = {}
        inputs_dict = {}
        blacklist = []
        payslip = self.env['hr.payslip'].browse(payslip_id)
        for worked_days_line in payslip.worked_days_line_ids:
            worked_days_dict[worked_days_line.code] = worked_days_line
        for input_line in payslip.input_line_ids:
            inputs_dict[input_line.code] = input_line

        categories = BrowsableObject(payslip.employee_id.id, {}, self.env)
        inputs = InputLine(payslip.employee_id.id, inputs_dict, self.env)
        worked_days = WorkedDays(payslip.employee_id.id, worked_days_dict, self.env)
        payslips = Payslips(payslip.employee_id.id, payslip, self.env)
        rules = BrowsableObject(payslip.employee_id.id, rules_dict, self.env)

        baselocaldict = {'categories': categories, 'rules': rules, 'payslip': payslips, 'worked_days': worked_days, 'inputs': inputs}
        #get the ids of the structures on the contracts and their parent id as well
        contracts = self.env['hr.contract'].browse(contract_ids)
        if len(contracts) == 1 and payslip.struct_id:
            structure_ids = list(set(payslip.struct_id._get_parent_structure().ids))
        else:
            structure_ids = contracts.get_all_structures()
        #get the rules of the structure and thier children
        rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
        #run the rules by sequence
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x:x[1])]
        sorted_rules = self.env['hr.salary.rule'].browse(sorted_rule_ids)

        if payslip.employee_id.id:
            if payslip.employee_id.is_teacher:
                if payslip.employee_id.is_permanent:
                    worked_days_line_ids = payslip.worked_days_line_ids
                    for contract in contracts:
                        employee = contract.employee_id
                        localdict = dict(baselocaldict, employee=employee, contract=contract)
                        for rule in sorted_rules:
                            key = rule.code + '-' + str(contract.id)
                            localdict['result'] = None
                            localdict['result_qty'] = 1.0
                            localdict['result_rate'] = 100
                            #check if the rule can be applied
                            if rule._satisfy_condition(localdict) and rule.id not in blacklist:
                                #compute the amount of the rule
                                amount, qty, rate = rule._compute_rule(localdict)
                                total_rate = 0.0
                                total_number_of_days = 0.0
                                key_timetables = {}
                                for worked_days_line_id in worked_days_line_ids:
                                    if worked_days_line_id.timetable_id.id:
                                        teacher_timetable_attendance_id = self.env['teacher.timetable.attendance'].search([('timetable_id', '=', worked_days_line_id.timetable_id.id)], limit=1)
                                        if teacher_timetable_attendance_id:
                                            total_rate += teacher_timetable_attendance_id.amount
                                            total_number_of_days += worked_days_line_id.number_of_days

                                            # worked_days_line_id.timetable_id.write({
                                            #     'worked_time': teacher_timetable_attendance_id.worked_time,
                                            #     'rate': teacher_timetable_attendance_id.rate,
                                            #     'amount': teacher_timetable_attendance_id.amount,
                                            # })

                                if rule.code == payslip.code:
                                    total_rate = round(total_rate, 2)
                                    amount = total_rate

                                _logger.info(f'----------- tototototototo key {key} -----------')
                                _logger.info(f'----------- tototototototo amount {amount} -----------')
                                _logger.info(f'----------- tototototototo qty {qty} -----------')
                                _logger.info(f'----------- tototototototo rate {rate} -----------')
                                _logger.info(f'----------- tototototototo total_rate {total_rate} -----------')
                                _logger.info(f'----------- tototototototo total_number_of_days {total_number_of_days} -----------')
                                _logger.info(f'----------- tototototototo contract {contract} -----------')

                                #check if there is already a rule computed with that code
                                previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                                #set/overwrite the amount computed for this rule in the localdict
                                tot_rule = contract.company_id.currency_id.round(amount * qty * rate / 100.0)
                                localdict[rule.code] = tot_rule
                                rules_dict[rule.code] = rule
                                #sum the amount for its salary category
                                localdict = _sum_salary_rule_category(localdict, rule.category_id, tot_rule - previous_amount)
                                #create/overwrite the rule in the temporary results
                                result_dict[key] = {
                                    'salary_rule_id': rule.id,
                                    'contract_id': contract.id,
                                    'name': rule.name,
                                    'code': rule.code,
                                    'category_id': rule.category_id.id,
                                    'sequence': rule.sequence,
                                    'appears_on_payslip': rule.appears_on_payslip,
                                    'condition_select': rule.condition_select,
                                    'condition_python': rule.condition_python,
                                    'condition_range': rule.condition_range,
                                    'condition_range_min': rule.condition_range_min,
                                    'condition_range_max': rule.condition_range_max,
                                    'amount_select': rule.amount_select,
                                    'amount_fix': rule.amount_fix,
                                    'amount_python_compute': rule.amount_python_compute,
                                    'amount_percentage': rule.amount_percentage,
                                    'amount_percentage_base': rule.amount_percentage_base,
                                    'register_id': rule.register_id.id,
                                    'amount': amount,
                                    'employee_id': contract.employee_id.id,
                                    'quantity': qty,
                                    'rate': rate,
                                }
                            else:
                                #blacklist this rule and its children
                                blacklist += [id for id, seq in rule._recursive_search_of_rules()]
                else:
                    worked_days_line_ids = payslip.worked_days_line_ids
                    for contract in contracts:
                        employee = contract.employee_id
                        localdict = dict(baselocaldict, employee=employee, contract=contract)
                        for rule in sorted_rules:
                            key = rule.code + '-' + str(contract.id)
                            localdict['result'] = None
                            localdict['result_qty'] = 1.0
                            localdict['result_rate'] = 100
                            #check if the rule can be applied
                            if rule._satisfy_condition(localdict) and rule.id not in blacklist:
                                #compute the amount of the rule
                                amount, qty, rate = rule._compute_rule(localdict)
                                total_rate = 0.0
                                total_number_of_days = 0.0
                                key_timetables = {}
                                for worked_days_line_id in worked_days_line_ids:
                                    if worked_days_line_id.timetable_id.id:
                                        teacher_timetable_attendance_id = self.env['teacher.timetable.attendance'].search([('timetable_id', '=', worked_days_line_id.timetable_id.id)], limit=1)
                                        if teacher_timetable_attendance_id:
                                            total_rate += teacher_timetable_attendance_id.amount
                                            total_number_of_days += worked_days_line_id.number_of_days

                                            # worked_days_line_id.timetable_id.write({
                                            #     'worked_time': teacher_timetable_attendance_id.worked_time,
                                            #     'rate': teacher_timetable_attendance_id.rate,
                                            #     'amount': teacher_timetable_attendance_id.amount,
                                            # })

                                if rule.code == payslip.code:
                                    total_rate = round(total_rate, 2)
                                    amount = total_rate

                                _logger.info(f'----------- tototototototo key {key} -----------')
                                _logger.info(f'----------- tototototototo amount {amount} -----------')
                                _logger.info(f'----------- tototototototo qty {qty} -----------')
                                _logger.info(f'----------- tototototototo rate {rate} -----------')
                                _logger.info(f'----------- tototototototo total_rate {total_rate} -----------')
                                _logger.info(f'----------- tototototototo total_number_of_days {total_number_of_days} -----------')
                                _logger.info(f'----------- tototototototo contract {contract} -----------')

                                #check if there is already a rule computed with that code
                                previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                                #set/overwrite the amount computed for this rule in the localdict
                                tot_rule = contract.company_id.currency_id.round(amount * qty * rate / 100.0)
                                localdict[rule.code] = tot_rule
                                rules_dict[rule.code] = rule
                                #sum the amount for its salary category
                                localdict = _sum_salary_rule_category(localdict, rule.category_id, tot_rule - previous_amount)
                                #create/overwrite the rule in the temporary results
                                result_dict[key] = {
                                    'salary_rule_id': rule.id,
                                    'contract_id': contract.id,
                                    'name': rule.name,
                                    'code': rule.code,
                                    'category_id': rule.category_id.id,
                                    'sequence': rule.sequence,
                                    'appears_on_payslip': rule.appears_on_payslip,
                                    'condition_select': rule.condition_select,
                                    'condition_python': rule.condition_python,
                                    'condition_range': rule.condition_range,
                                    'condition_range_min': rule.condition_range_min,
                                    'condition_range_max': rule.condition_range_max,
                                    'amount_select': rule.amount_select,
                                    'amount_fix': rule.amount_fix,
                                    'amount_python_compute': rule.amount_python_compute,
                                    'amount_percentage': rule.amount_percentage,
                                    'amount_percentage_base': rule.amount_percentage_base,
                                    'register_id': rule.register_id.id,
                                    'amount': amount,
                                    'employee_id': contract.employee_id.id,
                                    'quantity': qty,
                                    'rate': rate,
                                }
                            else:
                                #blacklist this rule and its children
                                blacklist += [id for id, seq in rule._recursive_search_of_rules()]
            else:
                for contract in contracts:
                    employee = contract.employee_id
                    localdict = dict(baselocaldict, employee=employee, contract=contract)
                    for rule in sorted_rules:
                        key = rule.code + '-' + str(contract.id)
                        localdict['result'] = None
                        localdict['result_qty'] = 1.0
                        localdict['result_rate'] = 100
                        #check if the rule can be applied
                        if rule._satisfy_condition(localdict) and rule.id not in blacklist:
                            #compute the amount of the rule
                            amount, qty, rate = rule._compute_rule(localdict)
                            #check if there is already a rule computed with that code
                            previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                            #set/overwrite the amount computed for this rule in the localdict
                            tot_rule = contract.company_id.currency_id.round(amount * qty * rate / 100.0)
                            localdict[rule.code] = tot_rule
                            rules_dict[rule.code] = rule
                            #sum the amount for its salary category
                            localdict = _sum_salary_rule_category(localdict, rule.category_id, tot_rule - previous_amount)
                            #create/overwrite the rule in the temporary results
                            result_dict[key] = {
                                'salary_rule_id': rule.id,
                                'contract_id': contract.id,
                                'name': rule.name,
                                'code': rule.code,
                                'category_id': rule.category_id.id,
                                'sequence': rule.sequence,
                                'appears_on_payslip': rule.appears_on_payslip,
                                'condition_select': rule.condition_select,
                                'condition_python': rule.condition_python,
                                'condition_range': rule.condition_range,
                                'condition_range_min': rule.condition_range_min,
                                'condition_range_max': rule.condition_range_max,
                                'amount_select': rule.amount_select,
                                'amount_fix': rule.amount_fix,
                                'amount_python_compute': rule.amount_python_compute,
                                'amount_percentage': rule.amount_percentage,
                                'amount_percentage_base': rule.amount_percentage_base,
                                'register_id': rule.register_id.id,
                                'amount': amount,
                                'employee_id': contract.employee_id.id,
                                'quantity': qty,
                                'rate': rate,
                            }
                        else:
                            #blacklist this rule and its children
                            blacklist += [id for id, seq in rule._recursive_search_of_rules()]

        return list(result_dict.values())

    # YTI TODO To rename. This method is not really an onchange, as it is not in any view
    # employee_id and contract_id could be browse records
    def onchange_employee_id(self, date_from, date_to, employee_id=False, contract_id=False):
        #defaults
        res = {
            'value': {
                'line_ids': [],
                #delete old input lines
                'input_line_ids': [(2, x,) for x in self.input_line_ids.ids],
                #delete old worked days lines
                'worked_days_line_ids': [(2, x,) for x in self.worked_days_line_ids.ids],
                #'details_by_salary_head':[], TODO put me back
                'name': '',
                'contract_id': False,
                'struct_id': False,
            }
        }
        if (not employee_id) or (not date_from) or (not date_to):
            return res
        ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
        employee = self.env['hr.employee'].browse(employee_id)
        locale = self.env.context.get('lang') or 'en_US'
        res['value'].update({
            'name': _('Salary Slip of %s for %s') % (employee.name, tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y', locale=locale))),
            'company_id': employee.company_id.id,
        })

        if not self.env.context.get('contract'):
            #fill with the first contract of the employee
            contract_ids = self.get_contract(employee, date_from, date_to)
        else:
            if contract_id:
                #set the list of contract for which the input have to be filled
                contract_ids = [contract_id]
            else:
                #if we don't give the contract, then the input to fill should be for all current contracts of the employee
                contract_ids = self.get_contract(employee, date_from, date_to)

        if not contract_ids:
            return res
        contract = self.env['hr.contract'].browse(contract_ids[0])
        res['value'].update({
            'contract_id': contract.id
        })
        struct = contract.struct_id
        if not struct:
            return res
        res['value'].update({
            'struct_id': struct.id,
        })
        #computation of the salary input
        contracts = self.env['hr.contract'].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from, date_to)
        input_line_ids = self.get_inputs(contracts, date_from, date_to)
        res['value'].update({
            'worked_days_line_ids': worked_days_line_ids,
            'input_line_ids': input_line_ids,
        })
        return res

    @api.onchange('employee_id', 'date_from', 'date_to')
    def onchange_employee(self):
        self.ensure_one()
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return
        employee = self.employee_id
        date_from = self.date_from
        date_to = self.date_to
        contract_ids = []

        ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
        locale = self.env.context.get('lang') or 'en_US'
        self.name = _('Salary Slip of %s for %s') % (employee.name, tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y', locale=locale)))
        self.company_id = employee.company_id

        if not self.env.context.get('contract') or not self.contract_id:
            contract_ids = self.get_contract(employee, date_from, date_to)
            if not contract_ids:
                return
            self.contract_id = self.env['hr.contract'].browse(contract_ids[0])

        if not self.contract_id.struct_id:
            return
        self.struct_id = self.contract_id.struct_id

        #computation of the salary input
        contracts = self.env['hr.contract'].browse(contract_ids)
        if contracts:
            worked_days_line_ids = self.get_worked_day_lines(contracts, date_from, date_to)
            worked_days_lines = self.worked_days_line_ids.browse([])
            for r in worked_days_line_ids:
                worked_days_lines += worked_days_lines.new(r)
            self.worked_days_line_ids = worked_days_lines

            input_line_ids = self.get_inputs(contracts, date_from, date_to)
            input_lines = self.input_line_ids.browse([])
            for r in input_line_ids:
                input_lines += input_lines.new(r)
            self.input_line_ids = input_lines
            return

    @api.onchange('contract_id')
    def onchange_contract(self):
        if not self.contract_id:
            self.struct_id = False
        self.with_context(contract=True).onchange_employee()
        return

    def get_salary_line_total(self, code):
        self.ensure_one()
        line = self.line_ids.filtered(lambda line: line.code == code)
        if line:
            return line[0].total
        else:
            return 0.0

class HrPayslipLine(models.Model):
    _name = 'hr.payslip.line'
    _inherit = 'hr.salary.rule'
    _description = 'Payslip Line'
    _order = 'contract_id, sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade')
    salary_rule_id = fields.Many2one('hr.salary.rule', string='Rule', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    contract_id = fields.Many2one('hr.contract', string='Contract', required=True, index=True)
    rate = fields.Float(string='Rate (%)', default=100.0)
    amount = fields.Float()
    quantity = fields.Float(default=1.0)
    total = fields.Float(compute='_compute_total', store=True, string='Total')

    @api.depends('quantity', 'amount', 'rate')
    def _compute_total(self):
        for record in self:
            if record.slip_id.employee_id.id:
                if record.slip_id.employee_id.is_teacher:
                    if record.slip_id.employee_id.is_permanent:
                        record.total = float(record.quantity) * record.amount * record.rate / 100
                    else:
                        record.total = float(record.quantity) * record.amount * record.rate / 100
                else:
                    record.total = float(record.quantity) * record.amount * record.rate / 100

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if 'employee_id' not in values or 'contract_id' not in values:
                payslip = self.env['hr.payslip'].browse(values.get('slip_id'))
                values['employee_id'] = values.get('employee_id') or payslip.employee_id.id
                values['contract_id'] = values.get('contract_id') or payslip.contract_id and payslip.contract_id.id
                if not values['contract_id']:
                    raise UserError(_('You must set a contract to create a payslip line.'))
        return super(HrPayslipLine, self).create(vals_list)

class HrPayslipWorkedDays(models.Model):
    _name = 'hr.payslip.worked_days'
    _description = 'Payslip Worked Days'
    _order = 'payslip_id, sequence'

    name = fields.Char(string='Description', required=True)
    payslip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(required=True, index=True, default=10)
    code = fields.Char(required=True, help="The code that can be used in the salary rules")
    number_of_days = fields.Float(string='Number of Days')
    number_of_hours = fields.Float(string='Number of Hours')
    contract_id = fields.Many2one('hr.contract', string='Contract', required=True,
        help="The contract for which applied this input")
    timetable_id = fields.Many2one('siantou.ems.timetable.timetable', string='Emploi du temps')
    date = fields.Date(string='Date du jour')
    start_time = fields.Float(string='Heure de début')
    end_time = fields.Float(string='Heure de fin')
    rate = fields.Float(string='Taux horaire', default=0.0)
    amount = fields.Float(string='Montant', default=0.0)

class HrPayslipInput(models.Model):
    _name = 'hr.payslip.input'
    _description = 'Payslip Input'
    _order = 'payslip_id, sequence'

    name = fields.Char(string='Description', required=True)
    payslip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(required=True, index=True, default=10)
    code = fields.Char(required=True, help="The code that can be used in the salary rules")
    amount = fields.Float(help="It is used in computation. For e.g. A rule for sales having "
                               "1% commission of basic salary for per product can defined in expression "
                               "like result = inputs.SALEURO.amount * contract.wage*0.01.")
    contract_id = fields.Many2one('hr.contract', string='Contract', required=True,
        help="The contract for which applied this input")

class HrPayslipRun(models.Model):
    _name = 'hr.payslip.run'
    _description = 'Payslip Batches'

    name = fields.Char(required=True)
    slip_ids = fields.One2many('hr.payslip', 'payslip_run_id', string='Payslips')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('close', 'Close'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft')
    date_start = fields.Date(
        string='Date From', required=True,
        default=lambda self: fields.Date.to_string(date.today().replace(day=1))
    )

    date_end = fields.Date(
        string='Date To', required=True,
        default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date())
    )

    credit_note = fields.Boolean(
        string='Credit Note',
        help="If its checked, indicates that all payslips generated from here are refund payslips."
    )

    def drsiantou_ems_payslip_run(self):
        return self.write({'state': 'draft'})

    def close_payslip_run(self):
        return self.write({'state': 'close'})

    def done_payslip_run(self):
        for line in self.slip_ids:
            line.action_payslip_done()
        return self.write({'state': 'done'})

    def unlink(self):
        for record in self:
            if record.state == 'done':
                raise ValidationError(_('You Cannot Delete Done Payslips Batches'))
        return super(HrPayslipRun, self).unlink()
