from odoo import models, fields, api
from datetime import timedelta
from odoo.exceptions import ValidationError  # Import the ValidationError class


class Year(models.Model):
    _name = 'siantou.ems.core.year'
    _description = 'Années académiques'

    # Nom de l'année académique
    name = fields.Char(
        'Nom',
        required=True
    )

    # Date de début de l'année académique
    start_time = fields.Date(
        'Date début',
        required=True
    )

    # Date de fin de l'année académique
    end_time = fields.Date(
        'Date fin',
        required=True
    )

    # Variable booléenne pour définir une année académique comme étant active (année académique en cours)
    active = fields.Boolean(
        'Actif',
        default=False
    )

    # Contrainte SQL pour empêcher d'avoir le même nom pour différentes années académiques
    _sql_constraints = [
        ('unique_name', 'unique(name)', 'L\'année académique doit être unique')
    ]

    # Contrainte logique pour empêcher d'avoir des années académiques qui se chevauchent
    @api.constrains('start_time', 'end_time')
    def _check_date_overlap(self):
        for record in self:
            if self.search([('id', '!=', record.id), ('start_time', '<=', record.end_time), ('end_time', '>=', record.start_time),]):
                raise ValidationError("Les années académiques ne peuvent se supperposer.")


    # Contrainte logique pour s'assurer que la date de fin est supérieure à la date de début
    @api.constrains('start_time', 'end_time')
    def _check_date_are_correct(self):
        for record in self:
            if record.start_time >= record.end_time:
                raise ValidationError("La date de fin doit être supérieure à la date de début.")


    # Contrainte logique pour empêcher d'avoir plusieurs années académiques actives simultannément
    @api.constrains('active')
    def _check_unique_active(self):
        years = self.search([])
        if len(years)>1:
            for record in self:
                if self.search([('id', '=', record.id), ('active', '=', True)]):
                    raise ValidationError("Il ne peut y avoir qu'une seule année académique active à la fois.")