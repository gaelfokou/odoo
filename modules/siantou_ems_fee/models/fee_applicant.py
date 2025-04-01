# -*- coding: utf-8 -*-
from asyncio.log import logger
from datetime import date

from odoo import fields, models, _, api
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger("+++++++++++++++++++++++++++++")

class StudentApplication(models.Model):
    _inherit = 'oe.school.student.enrollment'

