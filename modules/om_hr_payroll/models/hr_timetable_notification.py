# -*- coding:utf-8 -*-

import babel
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
from pytz import timezone
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
import pytz
import logging

_logger = logging.getLogger(__name__)


class HrTimetableNotification(models.Model):
    _name = 'hr.timetable.notification'
    _description = 'Timetable notification'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    template = fields.Char(string='Template')
    timetable_id = fields.Many2one('siantou.ems.timetable.timetable', string='Emplois du temps')
    date = fields.Date(string='Date',
        default=lambda r: date.today(),)

    status = fields.Selection([
        ('0', 'En attente'),
        ('1', 'Terminé'),
    ], 'Statut',
        default='0',
    )

    # Contrainte logique pour s'assurer que les heures de début et de fin sont définies
    @api.constrains('template')
    def _check_template(self):
        for record in self:
            if not record.template or record.template == '':
                raise ValidationError("Vous devez définir un template")

    @api.model
    def cron_timetable_notification(self):
        timetable_notifications = self.env['hr.timetable.notification'].search([
            ('status', '=', '0'),
        ])
        for timetable_notification in timetable_notifications:
            template = self.env.ref(timetable_notification.template)
            context = {
                'id': timetable_notification.id
            }
            template.with_context(context).send_mail(timetable_notification.id, force_send=True)
            timetable_notification.sudo().write({'status': '1'})
