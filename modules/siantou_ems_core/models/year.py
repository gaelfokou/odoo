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

    active_user_ids = fields.Many2many(
        'res.users',
        'active_user_year_rel',
        'year_id',
        'user_id',
        string='Utilisateurs associés actifs',
    )

    is_user_active = fields.Boolean(string='Utilisateur associé actif ?', compute='_compute_active')

    @api.depends('active_user_ids')
    def _compute_active(self):
        for record in self:
            years = self.env['siantou.ems.core.year'].sudo().search([
                ('id', '=', record.id),
                ('active_user_ids', '=', self.env.user.id),
            ])
            years = list(years)
            if len(years) > 0:
                record.is_user_active = True
            else:
                record.is_user_active = False

    @api.onchange('active_user_ids')
    def _onchange_active(self):
        for record in self:
            record._compute_active()

    @api.constrains('start_time', 'end_time')
    def _check_date(self):
        for record in self:
            years = self.env['siantou.ems.core.year'].search([
                ('id', '!=', record.id),
            ]).filtered(lambda rec: not (rec.start_time >= record.end_time or rec.end_time <= record.start_time))
            years = list(years)
            if len(years) > 0:
                raise ValidationError(f'Les dates de l\'année académique ne peuvent se chevaucher')
            if record.start_time >= record.end_time:
                raise ValidationError('La date de fin doit être supérieure à la date de début')

    @api.constrains('is_active', 'active_user_ids')
    def _check_unique_active(self):
        for record in self:
            if record.is_active:
                years = self.env['siantou.ems.core.year'].search([
                    ('id', '!=', record.id),
                    ('is_active', '=', True),
                ])
                years = list(years)
                if len(years) > 0:
                    raise ValidationError(f'Une année académique est déjà active')
            if len(record.active_user_ids.ids) > 0:
                for active_user_id in record.active_user_ids:
                    years = self.env['siantou.ems.core.year'].search([
                        ('id', '!=', record.id),
                        ('active_user_ids', '=', active_user_id.id),
                    ])
                    years = list(years)
                    if len(years) > 0:
                        raise ValidationError(f'Une année académique est déjà active pour l\'utilisateur {active_user_id.name}')

    @api.model
    def get_years(self, id=None):
        if id:
            years = self.env['siantou.ems.core.year'].sudo().search([
                ('id', '=', id),
                ('active_user_ids', '=', self.env.user.id),
            ])
            years = list(years)
            if len(years) == 0:
                years = self.env['siantou.ems.core.year'].sudo().search([
                    ('active_user_ids', '=', self.env.user.id),
                ])
                years = list(years)
                for year in years:
                    active_user_ids = [(3, active_user_id.id) for active_user_id in year.active_user_ids]
                    year.sudo().write({'active_user_ids': active_user_ids })
                years = self.env['siantou.ems.core.year'].sudo().search([])
                years = list(years)
                for year in years:
                    if year.id == id:
                        active_user_ids = [(4, self.env.user.id)]
                        year.sudo().write({'active_user_ids': active_user_ids })
        else:
            years = self.env['siantou.ems.core.year'].sudo().search([
                ('active_user_ids', '=', self.env.user.id),
            ])
            years = list(years)
            if len(years) == 0:
                years = self.env['siantou.ems.core.year'].sudo().search([])
                years = list(years)
                for year in years:
                    if year.is_active:
                        active_user_ids = [(4, self.env.user.id)]
                        year.sudo().write({'active_user_ids': active_user_ids })
        data = []
        years = self.env['siantou.ems.core.year'].sudo().search([])
        years = list(years)
        for year in years:
            key = {}
            key['id'] = year.id
            key['name'] = year.name
            key['start_time'] = year.start_time
            key['end_time'] = year.end_time
            key['is_active'] = year.is_user_active
            data.append(key)
        # return years.read()
        return data
