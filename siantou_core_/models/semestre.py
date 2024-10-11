from odoo import models, fields, api
from datetime import timedelta
from odoo.exceptions import ValidationError  # Import the ValidationError class


class SemestreAcademie(models.Model):
    _name = 'siantou.semestre'
    _description = 'Gestion des semestres Academiques'

    # Nom du semestre
    name = fields.Char(
        'Nom',
        required=True
    )

    # Date de début de l'année académique
    date_start = fields.Date(
        'Date début',
        required=True
    )

    # Date de fin de l'année académique
    date_end = fields.Date(
        'Date fin',
        required=True
    )


    annee_id = fields.Many2one(
        'siantou.annee',
        string='Année académique',
    )

    # Contrainte SQL pour empêcher d'avoir le même nom pour différents semestres
    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Ce semestre existe déjà'),
    ]

    # Contrainte logique pour empêcher d'avoir des semestres qui se chevauchent
    @api.constrains('date_start', 'date_end')
    def _check_date_overlap(self):
        for semestre in self:
            # Check for overlapping dates in other academic years
            overlapping_years = self.search([
                ('id', '!=', semestre.id),
                ('date_start', '<=', semestre.date_end),
                ('date_end', '>=', semestre.date_start),
            ])
            if overlapping_years:
                raise ValidationError("Les semestres ne peuvent se supperposer.")
