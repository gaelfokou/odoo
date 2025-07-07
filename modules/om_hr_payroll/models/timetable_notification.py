# -*- coding:utf-8 -*-

import babel
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
import pytz
import logging

DATE_FORMAT = '%Y-%m-%d'
DATE_FORMAT_FR = '%d/%m/%Y'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATETIME_FORMAT_FR = '%d/%m/%Y %H:%M'
TIME_FORMAT = '%H:%M:%S'
TIME_FORMAT_FR = '%H:%M'

_logger = logging.getLogger(__name__)

class TimetableNotification(models.Model):
    _name = 'siantou.ems.timetable.notification'
    _description = 'Timetable notification'

    template = fields.Char(string='Template')
    timetable_id = fields.Many2one('siantou.ems.timetable.timetable', string='Emploi du temps')
    attendance_id = fields.Many2one('daily.attendance', string='Daily attendance')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    date = fields.Date(string='Date', default=lambda r: date.today(),)
    message = fields.Text(string='Message')

    status = fields.Selection([
        ('pending', 'En attente'),
        ('sent', 'Envoyé'),
    ], 'Statut',
        default='pending',
    )

    # Contrainte logique pour s'assurer que les heures de début et de fin sont définies
    @api.constrains('template')
    def _check_template(self):
        for record in self:
            if not record.template or record.template == '':
                raise ValidationError("Vous devez définir un template")

    @api.model
    def cron_timetable_notification(self):
        _logger.info(f'+++++++++++ Cron Timetable Notification Executed +++++++++++')
        timetable_notifications = self.env['siantou.ems.timetable.notification'].sudo().search([
            ('status', '=', 'pending'),
        ])
        for timetable_notification in timetable_notifications:
            template = self.env.ref(timetable_notification.template)
            template.send_mail(timetable_notification.id, force_send=True)
            timetable_notification.sudo().write({'status': 'sent'})

    @api.model
    def cron_timetable_notification_suppression(self):
        _logger.info(f'+++++++++++ Cron Timetable Notification Suppression Executed +++++++++++')
        datetime_from = datetime.now()

        datetime_before = datetime_from - relativedelta(months=1)
        current_date = datetime_before.date()

        _logger.info(f'----------- tototototototo current_date {datetime.strftime(current_date, DATE_FORMAT)} -----------')

        timetable_notifications = self.env['siantou.ems.timetable.notification'].sudo().search([], order='date asc').filtered(lambda rec: rec.date <= current_date)
        timetable_notifications = list(timetable_notifications)
        for timetable_notification in timetable_notifications:
            timetable_notification.sudo().unlink()
