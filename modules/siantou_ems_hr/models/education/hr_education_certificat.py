# -*- coding:utf-8 -*-

from datetime import date

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError


class CertificatPersonnel(models.Model):
    _name = "hr.education.certificat"
    _description = "Model pour gérér les certificats du personnel"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    nom_certificat = fields.Char(string='Certificat', tracking=True)

    equivalence_id = fields.Many2one('hr.education.equivalence', string='Equivalence', tracking=True)

    annee_obtention = fields.Date(String="Date d'obtention")

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Personnel",
        ondelete="cascade",
    )

    ecole = fields.Char(string='Ecole ou Institut',required=True,tracking=True)

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
    