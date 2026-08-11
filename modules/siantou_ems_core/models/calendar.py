from odoo import models, fields, api, tools, _
from odoo.tools import format_date

import logging

_logger = logging.getLogger(__name__)

class Calendar(models.Model):
    _name = 'siantou.ems.core.calendar'
    _description = 'Calendrier académique'

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
