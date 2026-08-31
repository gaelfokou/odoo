from odoo import models, fields, api, tools, _
from datetime import timedelta
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class Year(models.Model):
    _name = 'siantou.ems.core.year'
    _description = 'Années académiques'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    name = fields.Char(
        string='Nom',
        required=True
    )

    start_time = fields.Date(
        string='Date de début',
        required=True
    )

    end_time = fields.Date(
        string='Date de fin',
        required=True
    )

    # Variable booléenne pour définir une année académique comme étant active (année académique en cours)
    is_active = fields.Boolean(string='Actif ?', default=False)

    is_valid = fields.Boolean(string='Valide ?', default=False)

    user_id = fields.Many2one(
        'res.users',
        string='Utilisateur associé',
        help='Utilisateur associé à cet étudiant'
    )

    @api.constrains('start_time', 'end_time', 'user_id')
    def _check_date(self):
        for record in self:
            if record.user_id.id:
                years = self.env['siantou.ems.core.year'].search([
                    ('id', '!=', record.id),
                    ('user_id', '=', record.user_id.id),
                ]).filtered(lambda rec: not (rec.start_time >= record.end_time or rec.end_time <= record.start_time))
                years = list(years)
                if len(years) > 0:
                    raise ValidationError(f'Les dates de l\'année académique ne peuvent se chevaucher pour l\'utilisateur {record.user_id.name}')
                if record.start_time >= record.end_time:
                    raise ValidationError('La date de fin doit être supérieure à la date de début')
            else:
                years = self.env['siantou.ems.core.year'].search([
                    ('id', '!=', record.id),
                    ('user_id', '=', False),
                ]).filtered(lambda rec: not (rec.start_time >= record.end_time or rec.end_time <= record.start_time))
                years = list(years)
                if len(years) > 0:
                    raise ValidationError(f'Les dates de l\'année académique ne peuvent se chevaucher')
                if record.start_time >= record.end_time:
                    raise ValidationError('La date de fin doit être supérieure à la date de début')

    @api.constrains('is_active', 'user_id')
    def _check_unique_active(self):
        for record in self:
            if record.user_id.id:
                if record.is_active:
                    years = self.env['siantou.ems.core.year'].search([
                        ('id', '!=', record.id),
                        ('user_id', '=', record.user_id.id),
                        ('is_active', '=', True),
                    ])
                    years = list(years)
                    if len(years) > 0:
                        raise ValidationError(f'Une année académique est déjà active pour l\'utilisateur {record.user_id.name}')
            else:
                if record.is_active:
                    years = self.env['siantou.ems.core.year'].search([
                        ('id', '!=', record.id),
                        ('user_id', '=', False),
                        ('is_active', '=', True),
                    ])
                    years = list(years)
                    if len(years) > 0:
                        raise ValidationError(f'Une année académique est déjà active')
