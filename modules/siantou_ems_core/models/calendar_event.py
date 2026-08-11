from odoo import models, fields, api, tools, _
from odoo.tools import format_date
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta, time
import holidays
import re
import psycopg2
import logging

_logger = logging.getLogger(__name__)

class CalendarEvent(models.Model):
    _name = 'siantou.ems.core.calendar.event'
    _description = 'Événement'

    name = fields.Char(
        string='Nom',
        required=True
    )

    start_date = fields.Date(
        string='Date de début',
        required=True
    )

    end_date = fields.Date(
        string='Date de fin',
    )

    formatted_date = fields.Char(
        string='Période',
        compute='_compute_formatted_date',
    )

    semester_id = fields.Many2one(
        'siantou.ems.core.year.semester',
        string='Semestre',
    )

    year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année académique',
        related='semester_id.year_id',
        store=True,
    )

    is_public_holiday = fields.Boolean(string='Est un jour férié ?', default=False)

    is_timetable_active = fields.Boolean(string='Emplois du temps actifs ?', default=True)

    @api.depends('start_date', 'end_date')
    def _compute_formatted_date(self):
        lang_code = self.env.context.get('lang') or self.env.user.lang
        for record in self:
            if not record.start_date:
                record.formatted_date = ""
            else:
                start_date = fields.Date.from_string(record.start_date)
                start_day = start_date.day
                start_day = str(start_day)
                if len(start_day) == 1:
                    start_day = '0{}'.format(start_day)
                start_month = format_date(self.env, start_date, date_format="MMMM")
                start_month = str(start_month)
                start_month = start_month.title()
                if not record.end_date or record.start_date == record.end_date:
                    record.formatted_date = f"{start_day} {start_month}"
                else:
                    end_date = fields.Date.from_string(record.end_date)
                    end_day = end_date.day
                    end_day = str(end_day)
                    if len(end_day) == 1:
                        end_day = '0{}'.format(end_day)
                    if start_date.month == end_date.month and start_date.year == end_date.year:
                        record.formatted_date = f"{start_day}-{end_day} {start_month}"
                    else:
                        end_month = format_date(self.env, end_date, date_format="MMMM")
                        end_month = str(end_month)
                        end_month = end_month.title()
                        record.formatted_date = f"{start_day} {start_month}-{end_day} {end_month}"

    @api.onchange('start_date', 'end_date')
    def _onchange_formatted_date(self):
        for record in self:
            record._compute_formatted_date()

    def create_calendar_event(self, student):
        try:
            ecole = re.sub('[^A-Za-z]+', '', student.school_id.name)
            ecole = ecole[:4]
            ecole = ecole.upper()
            if not student.matricule or not student.matricule.strip():
                matricule = ecole + self.env['ir.sequence'].next_by_code('oe.school.student')
                while True:
                    student_id = self.env['oe.school.student'].search([
                        ('id', '!=', student.id),
                        ('matricule', '=', matricule),
                    ], limit=1)
                    if student_id:
                        matricule = ecole + self.env['ir.sequence'].next_by_code('oe.school.student')
                    else:
                        break
            else:
                matricule = student.matricule
                while True:
                    if matricule.find('2024') != -1:
                        matricule = matricule.replace('2024', '')
                    else:
                        break
                matricule = '{}'.format(matricule)
            password = matricule
            if student.email and student.email.strip():
                email = student.email
            else:
                last_name = student.last_name if student.last_name else ''
                while True:
                    if last_name.find('  ') != -1:
                        last_name = last_name.replace('  ', ' ')
                    else:
                        break
                last_name = last_name.strip()
                last_name = last_name.split(' ')
                first_name = student.first_name if student.first_name else ''
                while True:
                    if first_name.find('  ') != -1:
                        first_name = first_name.replace('  ', ' ')
                    else:
                        break
                first_name = first_name.strip()
                first_name = first_name.split(' ')
                if len(first_name) > 1:
                    name = '{} {} {}'.format(first_name[0], last_name[0], first_name[1])
                else:
                    name = '{} {}'.format(first_name[0], last_name[0])
                # name = student.name
                while True:
                    if name.find('  ') != -1:
                        name = name.replace('  ', ' ')
                    else:
                        break
                name = name.strip()
                username = name.lower()
                username = username.split(' ')
                username = username[0:3]
                if len(username) == 1:
                    username = username[0]
                elif len(username) == 2:
                    username = '{}{}'.format(username[0][0:1], username[1])
                elif len(username) == 3:
                    username = '{}{}{}'.format(username[0][0:1], username[1], username[2][0:1])
                email = username + '@siantou.net'
                i = 0
                while True:
                    res_user_id = self.env['res.users'].search([
                        ('login', '=', email),
                    ], limit=1)
                    employee_id = self.env['hr.employee'].search([
                        ('work_email', '=', email),
                    ], limit=1)
                    student_id = self.env['oe.school.student'].search([
                        ('id', '!=', student.id),
                        ('email', '=', email),
                    ], limit=1)
                    if res_user_id or employee_id or student_id:
                        i = i + 1
                        email = username + f'{i}' + '@siantou.net'
                    else:
                        break
            student.write({
                'matricule': matricule,
                'email': email,
            })
            student.student_enroll_ids.create({
                'year_id': student.year_id.id,
                'school_id': student.school_id.id,
                'cycle_id': student.cycle_id.id,
                'field_of_study_id': student.field_of_study_id.id,
                'specialty_id': student.specialty_id.id,
                'option_id': student.option_id.id,
                'class_id': student.class_id.id,
                'type_cour': student.type_cour,
                'status_univ': student.status_univ,
                'session_lieu_obt': student.lieu_residence,
                'dern_etab_freq': student.lieu_residence,
                'level_id': student.level_id.id,
                'batch_id': student.batch_id.id,
                'student_id': student.id,
            })
            user_id = self.env['res.users'].search([
                ('login', '=', email),
            ], limit=1)
            if user_id:
                user_id.unlink()
            group_id = self.env.ref('base.group_portal')
            user_id = self.env['res.users'].with_context(no_reset_password=True).create({
                'login': email,
                'name': student.name,
                'password': password,
                'groups_id': [(6, 0, [group_id.id])],
            })
            # self.env.cr.commit()
        except psycopg2.errors.NotNullViolation as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except psycopg2.Error as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except Exception as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

    def action_create_all_calendar_event(self):
        student = self.env['oe.school.student'].search([
            ('id', '=', self.id),
        ], limit=1)
        if student:
            self.create_calendar_event(student)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
