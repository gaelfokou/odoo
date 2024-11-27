# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError  # Import the ValidationError class


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    percent = fields.Integer(string='Pourcentage de contrôle',config_parameter="siantou_ems_fee.percent",
                             default=60)



class BankAccountEnrollmentConfigSettings(models.TransientModel):
    _name = 'siantou.ems.fee.config.bank'
    _inherit=['mail.thread', 'mail.activity.mixin',]
    _description = "Configuration des numéros bancaires d'inscription"

    _sql_constraints = [
        ('unique_numero', 'unique(numero)', 'Ce nom existe déjà'),
    ]

    numero = fields.Char(string='Numéro', required=True)
    active = fields.Boolean(string='Actif', default=False)

    # Contrainte logique pour empêcher d'avoir plusieurs années académiques actives simultannément
    @api.constrains('active')
    def _check_unique_active(self):
        for record in self:
            if self.search([('id', '!=', record.id), ('active', '=', 'True')]):
                raise ValidationError("Il ne peut y avoir qu'une seule configuration des numéros bancaires d'inscription active à la fois.")