import math
import threading
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, AccessError, ValidationError
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class DataRequestWizard(models.TransientModel):
    _name = 'siantou.ems.core.data_request_wizard'
    _description = 'Données requises'

    email = fields.Char(
        string='E-mail',
        required=True,
    )

    phone = fields.Char(
        string='Numéro de téléphone',
        required=True,
    )

    def submit_data_request(self):
        check_classroom_slot = None

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
