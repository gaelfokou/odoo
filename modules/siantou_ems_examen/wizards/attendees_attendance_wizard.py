# -*- coding: utf-8 -*-
import logging
from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
from bs4 import BeautifulSoup

_logger = logging.getLogger(__name__)

class TicketMergeWizard(models.TransientModel):
    _name = 'session.line.attende.attend'
    _description = 'Ticket Reopen Wizard'

    exam_attendee_ids = fields.Many2many(
        'session.line.attende', 
        default=lambda self: self.env.context.get('active_ids'),
        string="Participants"
    )

    status = fields.Selection([
            ('P', 'Présent'),
            ('A', 'Abscent'),
        ], 
        string='Statut', 
        required=True
    )

    def action_apply_attendance(self):
        _logger.info(self.exam_attendee_ids)
        _logger.info(self.env.context.get('active_ids'))
        for attendee in self.exam_attendee_ids:
            attendee.write({
                'status': self.status, 
            })