# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import logging
import os
import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError
from odoo.modules.module import get_resource_path

from random import randrange
from PIL import Image

_logger = logging.getLogger(__name__)


class Company(models.Model):
    _inherit = "res.company"
    
    is_school = fields.Boolean(string='Ecole')
    school_type = fields.Selection(
        [
            ('k12','Ecole K12'),
            ('col','Collège'),
            ('uni','Université'),
            ('ti','Institut professionnel et technique'),
            ('ling','Centre d\'apprentissage des langues'),
            ('art','École d\'art'),
            ('special','École pour personnes à besoins spécifiques'),
        ],
        default='uni', string='Type d\'école',
    )
    use_batch = fields.Boolean('Activer les lots')
    use_section = fields.Boolean('Activer les sections')
    use_credit_hours = fields.Boolean('Activer le volume horaire')
    