from odoo import models, fields


class UniversityResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    is_university_calendar = fields.Boolean(
        string="Est un calendrier scolaire"
    )
