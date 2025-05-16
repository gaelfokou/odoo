# -*- coding:utf-8 -*-

from datetime import date

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError


class AnnulSuspension(models.Model):
    _name = "hr.annul.suspension"
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

    suspension_id = fields.Many2one(
        "hr.employee.discipline",
        string="Suspension",
        states={"draft": [("readonly", False)]},
    )

    name = fields.Char(
        string="Code",
        related='suspension_id.name',
        states={"draft": [("readonly", False)]},
    )

    reference = fields.Char(
        string="Référence de l'acte",
        related='suspension_id.reference',
        states={"draft": [("readonly", False)]},
    )

    date_suspension = fields.Date(
        string="Date de sanction",
        related='suspension_id.date',
        states={"draft": [("readonly", False)]},
    )

    date = fields.Date(
        "Date de levée",
        default=lambda r: date.today(),
        states={"draft": [("readonly", False)]},
    )

    document = fields.Binary(string="Fichier joint", tracking=True,states={
        'draft': [('readonly', False)]})

    file_name = fields.Char("Nom du fichier", tracking=True,states={
        'draft': [('readonly', False)]})

    description = fields.Text("Note",states={
        'draft': [('readonly', False)]})

    state = fields.Selection(
        [
            ("draft", "Brouillon"),
            ("validate", "Valider"),
            ("confirm", "Confirmer"),
            ("cancel", "Annuler"),
        ],
        string="state",
        default="draft"
    )

    type_saction = fields.Selection(
        [("suspendu", "Suspendu")],
        string="Type suspension",
        default="suspendu",
        states={"draft": [("readonly", False)]},
    )

    def action_valider(self):
        sequence_obj = self.env["ir.sequence"]
        for rec in self:
            rec.name = sequence_obj.next_by_code("aft_hr.annul_suspension")
            rec.state = "validate"

    def action_annuler(self):
        for rec in self:
            rec.state = "cancel"

    def action_confirmer(self):
        for rec in self:
            if rec.employee_id:
                rec.employee_id.state = "actif"
                rec.state = "confirm"

    @api.onchange("type_saction")
    def _onchange_type_suspension(self):
        for rec in self:
            domain = []
            if rec.type_saction:
                domain.append(("state", "=", rec.type_saction))

            return {"domain": {"employee_id": domain}}

    @api.onchange("employee_id")
    def _onchange_suspension(self):
        for rec in self:
            domain = []
            if rec.employee_id:
                domain.append(("employee_id", "=", rec.employee_id.id))

            return {"domain": {"suspension_id": domain}}
