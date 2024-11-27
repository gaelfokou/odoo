# -*- coding:utf-8 -*-

from datetime import date

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError


class LicencierEmployee(models.Model):
    _name = "hr.carriere.licencier"
    _description = "Model pour anneler une suspension"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char("Code")

    employee_id = fields.Many2one(
        "hr.employee",
        string="Personnel",
        required=True,
        tracking=True,
        states={"draft": [("readonly", False)]},
    )

    description = fields.Text(
        string="Description",
        required=True,
        tracking=True,
        states={"draft": [("readonly", False)]},
    )

    motif_licenciement_ids = fields.Many2many(
        "hr.motif.licenciement",
        string="Motif(s) de licenciement",
        required=True,
        tracking=True,
        states={"draft": [("readonly", False)]},
    )

    document = fields.Binary(string="Pièce justificative", tracking=True)

    file_name = fields.Char("Nom du fichier", tracking=True)

    date = fields.Date(
        string="Date de licenciément",
        default=lambda r: date.today(),
        required=True,
        tracking=True,
        states={"draft": [("readonly", False)]},
    )

    state = fields.Selection(
        [
            ("draft", "Brouillon"),
            ("validate", "Valider"),
            ("confirm", "Confirmer"),
            ("cancel", "Annuler"),
        ],
        string="state",
        default="draft",
        states={"draft": [("readonly", False)]},
    )

    def action_valider(self):
        sequence_obj = self.env["ir.sequence"]
        for rec in self:
            rec.name = sequence_obj.next_by_code("aft_hr.licencier")
            rec.state = "validate"

    def action_annuler(self):
        for rec in self:
            rec.state = "cancel"

    def action_confirmer(self):
        for rec in self:
            if rec.employee_id:
                if rec.employee_id.state == "liencie":
                    raise ValidationError("Oups ! Ce personnel est déja licencie")
                else:
                    rec.employee_id.state = "liencie"
                    rec.state = "confirm"
