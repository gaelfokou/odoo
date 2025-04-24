import base64
import io
import logging
import os
import re

from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError, UserError
from odoo.modules.module import get_resource_path

from random import randrange
from PIL import Image

_logger = logging.getLogger(__name__)

class University(models.Model):
    _inherit = 'res.company'

    is_university = fields.Boolean(
        string='Est une université',
        default=True,
        help='Précise si c\'est une institution d\'enseignement'
    )

