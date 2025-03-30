
from odoo import models, fields, Command
from odoo.tools import populate
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    # cycle_id = fields.Many2one(
    #     'oe.school.course',
    #     string='Cursus ou Cycle',
    #     required=True
    # )
    # school_id = fields.Many2one(
    #     'siantou.ems.core.school',
    #     string='Ecole',
    #     related='field_of_study_id.school_id'
    # )
    # field_of_study_id = fields.Many2one(
    #     'siantou.ems.core.field_of_study',
    #     string='Filière',
    #     required=True,
    # )
    # specialty_id = fields.Many2one(
    #     'siantou.ems.core.specialty',
    #     string='Spécialité',
    # )
    # year_id = fields.Many2one(
    #     "siantou.ems.core.year",
    #     string="Année académique",
    #     required=True,
    #     # default=lambda self: self.env['siantou.ems.core.year'].search(
    #     #     [('active', '=', True)],
    #     #     limit=1
    #     # )
    # )
    # level_id = fields.Many2one("siantou.ems.core.level", string="Niveau", required=True)

