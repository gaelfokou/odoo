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

    def create_calendar_event(self, semester):
        try:
            locale = self.env.context.get('lang') or 'en_US'
            if semester.start_time.year == semester.end_time.year:
                cm_holidays = holidays.CM(years=semester.start_time.year, language=locale)
            else:
                cm_holidays = holidays.CM(years=range(semester.start_time.year, semester.end_time.year), language=locale)
            holiday_dates = {
                date: name for date, name in sorted(cm_holidays.items()) if date.year >= semester.start_time.year and date.year <= semester.end_time.year  # S'assurer que c'est pour l'année courante
            }
            for holiday_date, holiday_name in holiday_dates.items():
                existing_dates = [event.start_date for event in self.env['siantou.ems.core.calendar.event'].search([
                    ('start_date', '=', holiday_date),
                    ('end_date', '=', holiday_date),
                ])]
                existing_dates = list(existing_dates)
                if len(existing_dates) == 0:
                    if holiday_date >= semester.start_time and holiday_date <= semester.end_time:
                        self.env['siantou.ems.core.calendar.event'].create({
                            'name': holiday_name,
                            'start_date': holiday_date,
                            'end_date': holiday_date,
                            'semester_id': semester.id,
                            'is_public_holiday':True
                        })
                    else:
                        self.env['siantou.ems.core.calendar.event'].create({
                            'name': holiday_name,
                            'start_date': holiday_date,
                            'end_date': holiday_date,
                            'is_public_holiday':True
                        })

            _logger.info(f'----------- tototototototo semester.name {semester.name} -----------')
            _logger.info(f'----------- tototototototo semester.start_time {semester.start_time} -----------')
            _logger.info(f'----------- tototototototo semester.end_time {semester.end_time} -----------')
            _logger.info(f'----------- tototototototo len holiday_dates {len(holiday_dates.keys())} -----------')
            _logger.info(f'----------- tototototototo holiday_dates {list(holiday_dates.values())} -----------')

            # self.env.cr.commit()
        except psycopg2.errors.NotNullViolation as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except psycopg2.Error as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')
        except Exception as error:
            _logger.info(f'----------- tototototototo Exception {error} -----------')

    def action_create_all_calendar_event(self):
        semesters = self.env['siantou.ems.core.year.semester'].search([
            ('year_id.is_active', '=', True)
        ])
        semesters = list(semesters)
        if len(semesters) == 0:
            raise UserError(_("Aucun semestre trouvé pour l'année académique active. Veuillez d'abord configurer les semestres."))

        for semester in semesters:
            self.create_calendar_event(semester)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
