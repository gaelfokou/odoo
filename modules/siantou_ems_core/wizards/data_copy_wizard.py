from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from pprint import pformat
import pandas as pd
import numpy as np
import re
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import copy
import logging

DATE_FORMAT = '%Y-%m-%d'
DATE_FORMAT_FR = '%d/%m/%Y'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATETIME_FORMAT_FR = '%d/%m/%Y %H:%M'
TIME_FORMAT = '%H:%M:%S'
TIME_FORMAT_FR = '%H:%M'

STATUS_TIMETABLE = {
    'pending': 'En attente',
    'progress': 'En cours',
    'present': 'Présent',
    'absent': 'Absent',
    'permission': 'Permission',
    'exception': 'Exception',
    'delay': 'Retard',
}

TYPE_COUR = {
    'cj': 'Cours du jour',
    'cs': 'Cours du soir',
}

_logger = logging.getLogger(__name__)


class DataCopyWizard(models.TransientModel):
    _name = 'data.copy.wizard'
    _description = 'Copie des autres données'

    source_year_id = fields.Many2one(
        'siantou.ems.core.year',
        'Année académique source',
        required=True,
    )

    destination_year_id = fields.Many2one(
        'siantou.ems.core.year',
        'Année académique destination',
        required=True,
    )

    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
    )

    def action_copy(self):
        domain = []

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
