# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class Displine(models.Model):
    _name = "hr.employee.discipline"
    _description = "Liste des sanction pas personnel"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char("Code")

    reference = fields.Char(string="Référence de l'acte", states={"confirmer": [("readonly", False)]})

    employee_id = fields.Many2one(
        "hr.employee",
        string="Personnel",
        required=True,
        states={"confirmer": [("readonly", False)]},
    )

    date = fields.Date(
        string="Date de sanction",
        required=True,
        states={"confirmer": [("readonly", False)]},
    )

    type_sanction = fields.Many2one(
        "hr.employee.type.sanction",
        string="Sanction",
        required=True,
        states={"confirmer": [("readonly", False)]},
    )

    categorie_sanction = fields.Selection(
        [
            ("positive", "Positive"),
            ("negative", "Négative"),
            ("suspendu", "Suspendu"),
            ("mis_a_pied", "Mise à pied")
        ],
        string="Type de sanction",
        default="positive",
        states={"confirmer": [("readonly", False)]},
    )

    fichier = fields.Binary(string="Joindre un document ")

    state = fields.Selection(
        selection=[
            ("draft", "Initialiser"),
            ("valider", "Valider"),
            ("confirmer", "Confirmer"),
            ("annuler", "Annuler"),
        ],
        default="draft",
        string="Statut",
        tracking=True,
    )

    @api.constrains("date")
    def _constrains_birthday(self):
        for rec in self:
            if rec.date:
                if rec.date > fields.Date.today():
                    raise ValidationError(
                        "la date de sanction ne peut pas etre supérieur à la date du jour"
                    )

    @api.onchange("categorie_sanction")
    def _onchange_categorie_sanction(self):
        for rec in self:
            domain = []
            if rec.categorie_sanction:
                if rec.categorie_sanction == "positive":
                    domain.append(("type_sanction", "=", "positive"))
                elif rec.categorie_sanction == "negative":
                    domain.append(("type_sanction", "=", "negative"))
                elif rec.categorie_sanction == "suspendu":
                    domain.append(("type_sanction", "=", "suspendu"))
                elif rec.categorie_sanction == "mis_a_pied":
                    domain.append(("type_sanction", "=", "mis_a_pied"))
                elif rec.categorie_sanction == "malade":
                    domain.append(("type_sanction", "=", "malade"))
            return {"domain": {"type_sanction": domain}}

    def action_valider(self):
        sequence_obj = self.env["ir.sequence"]
        for record in self:
            record.name = sequence_obj.next_by_code("aft_hr.discipline")
            record.state = "valider"

    def action_confirmer(self):
        for rec in self:
            if rec.employee_id:
                if (
                    rec.employee_id.state == "suspendu"
                    or rec.employee_id.state == "liencie"
                ):
                    raise ValidationError(" OUps !!Ce personnel est déja suspendu ")
                else:
                    if rec.categorie_sanction and rec.employee_id:
                        if rec.categorie_sanction == "suspendu":
                            rec.employee_id.state = "suspendu"
                        elif rec.categorie_sanction == "mis_a_pied":
                            rec.employee_id.state = "suspendu"
                        elif rec.categorie_sanction == "malade":
                            rec.employee_id.state = "suspendu"
                    rec.state = "confirmer"

    def action_annuler(self):
        for rec in self:
            rec.state = "annuler"
