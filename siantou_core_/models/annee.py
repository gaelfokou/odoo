from odoo import models, fields, api
from datetime import timedelta
from odoo.exceptions import ValidationError  # Import the ValidationError class


class AnneeAcademie(models.Model):
    _name = 'siantou.annee'
    _description = 'Gestion des années académiques'

    # Nom de l'année académique
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
    # Variable booléenne pour définir une année académique comme étant active (année académique en cours)
    is_actif = fields.Boolean(
        'Actif',
        default=False
    )

    # Contrainte SQL pour empêcher d'avoir le même nom pour différentes années académiques
    _sql_constraints = [
        ('unique_name', 'unique(name)', "L'année académique doit être unique"),
        ('unique_name', 'unique(is_actif)', 'Une année est déjà activé'),
    ]

    # Contrainte logique pour empêcher d'avoir des années académiques qui se chevauchent
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

    # Contrainte logique pour empêcher d'avoir plusieurs années académiques actives simultannément
    @api.constrains('is_actif')
    def _check_unique_active(self):
        for year in self:
            active_year = self.search([
                ('id', '!=', year.id),
                ('is_actif', '=', True)
            ])
            if active_year:
                raise ValidationError("Il ne peut y avoir qu'une seule année académique active à la fois.")
