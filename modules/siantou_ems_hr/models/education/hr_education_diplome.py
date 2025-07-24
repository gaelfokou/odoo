# -*- coding:utf-8 -*-

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from datetime import date
import logging

_logger = logging.getLogger(__name__)

class DiplomeAvailability(models.Model):
    _name = 'hr.education.diplome.availability'
    _description = 'Diplôme disponible'

    code = fields.Char(string="Code", required=True,)

    name = fields.Char(string="Diplôme", required=True)

    diplome_ids = fields.One2many(
        'hr.education.diplome',
        'diplome_availability_id',
        'Diplômes'
    )

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code du diplôme doit être unique.'),
        ('unique_name', 'unique(name)', 'Le nom du diplôme doit être unique.'),
    ]

class DiplomePersonnel(models.Model):
    _name = 'hr.education.diplome'
    _description = "Model pour gérér les diplomes du personnel"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string='Diplôme', related='diplome_availability_id.name', store=True, tracking=True)

    diplome_availability_id = fields.Many2one(
        'hr.education.diplome.availability',
        'Diplôme disponible',
        required=True,
        ondelete='cascade'
    )

    equivalence_id = fields.Many2one('hr.education.equivalence', string='Equivalence', tracking=True)

    annee_obtention = fields.Date(String="Date d'obtention")

    employee_id = fields.Many2one(
        'hr.employee',
        'Personnel',
        ondelete='cascade'
    )

    ecole = fields.Char(string='Ecole', tracking=True)

    domaine = fields.Char(string='Domaine', tracking=True)

    document = fields.Binary(string="Fichier joint", tracking=True)

    file_name = fields.Char("Nom du fichier", tracking=True)

    @api.constrains('annee_obtention')
    def _constrains_annee_obtention(self):
        for rec in self:
            if rec.annee_obtention:
                if rec.annee_obtention >= fields.Date.today():
                    raise ValidationError(
                        "La date d'obtention ne eput etre supérieure à la date courante"
                    )
    