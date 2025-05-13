# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _
import logging

_logger = logging.getLogger(__name__)

class DailyAttendance(models.Model):
    _inherit = 'daily.attendance'

    def action_open_filter(self):
        pass

    def action_reset_filter(self):
        pass

    def action_print_pdf(self):
        pass
