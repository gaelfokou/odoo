# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AcademicYear(models.Model):
    _name = 'is.university.academic_year'
    _description = 'Années académiques'

    name = fields.Char('Nom', required=True)
    date_start = fields.Date('Date de début', required=True)
    date_end = fields.Date('Date de fin', required=True)
    active = fields.Boolean('Actif', default=True)

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Le nom de l\'année académique doit être unique.')
    ]

    @api.constrains('date_start', 'date_end')
    def _check_date_overlap(self):
        for year in self:
            overlapping_years = self.search([
                ('id', '!=', year.id),
                ('date_start', '<=', year.date_end),
                ('date_end', '>=', year.date_start),
            ])
            if overlapping_years:
                raise ValidationError("Les années académiques ne peuvent se supperposer.")

    @api.constrains('active')
    def _check_unique_active(self):
        if self.active:
            other_active_years = self.search([('id', '!=', self.id), ('active', '=', True)])
            if other_active_years:
                raise ValidationError("Il ne peut y avoir qu'une seule année académique active à la fois.")
