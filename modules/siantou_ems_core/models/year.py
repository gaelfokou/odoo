from odoo import models, fields, api, tools, _
from datetime import timedelta
from odoo.exceptions import UserError, ValidationError

class Year(models.Model):
    _name = 'siantou.ems.core.year'
    _description = 'Années académiques'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    # Nom de l'année académique
    name = fields.Char(
        'Nom',
        required=True
    )

    # Date de début de l'année académique
    start_time = fields.Date(
        'Date de début',
        required=True
    )

    # Date de fin de l'année académique
    end_time = fields.Date(
        'Date de fin',
        required=True
    )

    # Variable booléenne pour définir une année académique comme étant active (année académique en cours)
    is_active = fields.Boolean(string='Actif', default=False)

    # Contrainte logique pour empêcher d'avoir des années académiques qui se chevauchent
    @api.constrains('start_time', 'end_time')
    def _check_date_overlap(self):
        for record in self:
            years = self.env['siantou.ems.core.year'].search([('id', '!=', record.id)]).filtered(lambda rec: not (rec.start_time >= record.end_time or rec.end_time <= record.start_time))
            years = list(years)
            if len(years) > 0:
                raise ValidationError('Les années académiques ne peuvent se supperposer')

    # Contrainte logique pour s'assurer que la date de fin est supérieure à la date de début
    @api.constrains('start_time', 'end_time')
    def _constrains_date(self):
        for record in self:
            if record.start_time >= record.end_time:
                raise ValidationError('La date de fin doit être supérieure à la date de début')

    # Contrainte logique pour empêcher d'avoir plusieurs années académiques actives simultannément
    @api.constrains('is_active')
    def _check_unique_active(self):
        for record in self:
            if record.is_active:
                years = self.env['siantou.ems.core.year'].search([
                    ('id', '!=', record.id),
                    ('is_active', '=', True),
                ])
                years = list(years)
                if len(years) > 0:
                    raise ValidationError(f"Année académique active déjà définie")
