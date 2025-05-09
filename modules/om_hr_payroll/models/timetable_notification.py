# -*- coding:utf-8 -*-

import babel
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
import pytz
import logging

_logger = logging.getLogger(__name__)

class TimetableNotification(models.Model):
    _name = 'siantou.ems.timetable.notification'
    _description = 'Timetable notification'

    template = fields.Char(string='Template')
    timetable_id = fields.Many2one('siantou.ems.timetable.timetable', string='Emplois du temps')
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
        timetable_notifications = self.env['siantou.ems.timetable.notification'].search([
            ('status', '=', 'pending'),
        ])
        for timetable_notification in timetable_notifications:
            template = self.env.ref(timetable_notification.template)
            template.send_mail(timetable_notification.id, force_send=True)
            timetable_notification.sudo().write({'status': 'sent'})
