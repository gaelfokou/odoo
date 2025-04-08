from odoo import models, fields, api
from datetime import timedelta
from odoo.exceptions import ValidationError  # Import the ValidationError class


class SchoolAcademicYear(models.Model):
    _name = 'oe.school.year'
    _description = 'oe.academic.year'
 
    name = fields.Char('Nom',required=True)
    date_start = fields.Date('Date début', required = True)
    date_end = fields.Date('Date fin',required = True)
    active = fields.Boolean('Actif', default=True)

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'L\'année académique doit être unique')
    ]
    
    @api.constrains('date_start', 'date_end')
    def _check_date_overlap(self):
        for year in self:
            # Check for overlapping dates in other academic years
            overlapping_years = self.search([
                ('id', '!=', year.id),
                ('date_start', '<=', year.date_end),
                ('date_end', '>=', year.date_start),
            ])
            if overlapping_years:
                raise ValidationError("Les années académiques ne peuvent se supperposer.")