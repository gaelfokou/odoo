# -*- coding:utf-8 -*-

from datetime import date

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError


class AnnulLicenciement(models.Model):
    _name = "hr.annul.licenciement"
    _description = "Model pour anneler un licenciement"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char("Code")

    employee_id = fields.Many2one(
        "hr.employee",
        string="Personnel",
        required=True,
        tracking=True,
        domain=[("state", "=", "liencie")],
        states={"draft": [("readonly", False)]},
    )

    reference = fields.Char(
        string="Référence de l’Acte ",
        required=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )
    
    date = fields.Date(
        "Date de levée",
        default=lambda r: date.today(),
        states={"draft": [("readonly", False)]},
    )

    line_licenciement_ids = fields.One2many(
        "hr.line.licenciement",
        "annul_licenciement_id",
        string="Line de lienciement",
        states={"draft": [("readonly", False)]},
    )

    document = fields.Binary(string="Pièce justificative", tracking=True,states={
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

    def action_valider(self):
        sequence_obj = self.env["ir.sequence"]
        for rec in self:
            rec.name = sequence_obj.next_by_code("aft_hr.annuler_licenciement")
            rec.state = "validate"

    def action_annuler(self):
        for rec in self:
            rec.state = "cancel"

    def action_confirmer(self):
        for rec in self:
            if rec.employee_id:
                rec.employee_id.state = "actif"
                rec.state = "confirm"

    @api.onchange("employee_id")
    def _onchange_licenciement(self):
        line_obj = self.env["hr.line.licenciement"]
        for rec in self:
            if rec.employee_id:
                result_id = self.env["hr.carriere.licencier"].search(
                    [("employee_id", "=", rec.employee_id.id)]
                )

                lines_ids = []

                for emp in result_id:
                    l = line_obj.create(
                        {
                            "name": emp.name,
                            "date": emp.date,
                            "motif_id": emp.motif_licenciement_ids.id,
                            "description": emp.description,
                        }
                    )
                    lines_ids.append(l.id)
                rec.line_licenciement_ids = [(6, 0, lines_ids)]


class LineLicenciement(models.Model):
    _name = "hr.line.licenciement"
    _description = "Line de licenciement"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char("code")

    licenciement_id = fields.Many2one("hr.carriere.licencier", string="licenciement")

    motif_id = fields.Many2one("hr.motif.licenciement", string="Motif")

    annul_licenciement_id = fields.Many2one("hr.annul.licenciement")

    description = fields.Text("description")

    date = fields.Date("Date")
