from datetime import date

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

NO_DEST_UNIT = _("Veuillez définir l'unité ou le service")

SUBJECT_NEW_AVA = _("Nouvel Affectaion")
SUBJECT_VAL_AVA = _("Affectaion validé")
SUBJECT_CON_AVA = _("Affectaion confirmé")
SUBJECT_TER_AVA = _("Affectaion terminé")
SUBJECT_ANN_AVA = _("Affectaion annulé")
BODY_NEW_AVA = _("l'Affectaion de l'employé %s a été créé")
BODY_VAL_AVA = _("l'Affectaion de l'employé %s a été validé")
BODY_CON_AVA = _("l'Affectaion de l'employé %s a été confirmé")
BODY_TER_AVA = _("l'Affectaion de l'employé %s est terminé")
BODY_ANN_AVA = _("l'Affectaion de l'employé %s est annulé")


class HrAffectation(models.Model):
    _name = "hr.carriere.affectation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Gestion des affectations ou mutations des Personnels"

    name = fields.Char(string="Code")

    reference = fields.Char(
        string="Référence de l’Acte ",
        required=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )

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

    date_affectation = fields.Date(
        string="Date de signature de l'affectation",
        default=date.today(),
        required=True,
        tracking=True,
        states={"draft": [("readonly", False)]},
    )

    employee_id = fields.Many2one(
        "hr.employee",
        string="Personnel",
        required=True,
        tracking=True,
        states={"draft": [("readonly", False)]},
    )

    department_src_id = fields.Many2one(
        "hr.department",
        string="Unité de travail actuelle",
        tracking=True,
        states={"draft": [("readonly", False)]},
    )

    department_dst_id = fields.Many2one(
        "hr.department",
        string="Unité de travail de destination",
        required=True,
        tracking=True,
        states={"draft": [("readonly", False)]},
    )

    date_effective = fields.Date(
        string="Date effective",
        tracking=True,
        required=True,
        states={"draft": [("readonly", False)]},
    )

    document = fields.Binary(
        string="Fichier joint",
        help="La note d'affectation",
        tracking=True,
        required=True,
        states={"draft": [("readonly", False)]},
    )

    file_name = fields.Char(
        "Nom du fichier",
        tracking=True,
        states={"draft": [("readonly", False)]},
    )

    description = fields.Text(
        "Note sur l'affectation",
        tracking=True,
        states={"draft": [("readonly", False)]},
    )

    @api.constrains("department_src_id")
    def _constrains_department_src_id(self):
        for rec in self:
            if not rec.department_src_id:
                raise UserError(
                    """Veuillez renseigner l'unité de travail actuelle du personnel"""
                )

    def action_valider(self):
        sequence_obj = self.env["ir.sequence"]
        for record in self:
            record.name = sequence_obj.next_by_code("aft_hr.affectation")
            # record.message_post(
            #     body=BODY_VAL_AVA % record.employee_id.name,
            #     subject=SUBJECT_VAL_AVA,
            #     message_type='notification',
            #     subtype="aft_hr.avancement_brouillon")
            record.state = "valider"

    def action_confirmer(self):
        for record in self:
            record.employee_id.department_id = record.department_dst_id.id

            # if record.date_effective:
            #     today = fields.Date.today()
            #     diff = relativedelta(today, record.date_effective)
            #     record.employee_id.date_entry_fonction = record.date_effective
            #     record.employee_id.duration_in_fonction = diff.years
            # else:
            #     record.employee_id.duration_in_fonction = 0
            # record.message_post(
            #     body=BODY_CON_AVA % record.employee_id.name,
            #     subject=SUBJECT_CON_AVA,
            #     message_type='notification',
            #     subtype="aft_hr.avancement_confirme")

            record.state = "confirmer"

    def action_draft(self):
        for record in self:
            record.state = "draft"

    def action_cancel(self):
        for record in self:
            # record.message_post(
            #     body=BODY_ANN_AVA % record.employee_id.name,
            #     subject=SUBJECT_ANN_AVA,
            #     message_type='notification',
            #     subtype="aft_hr.avancement_annule")
            record.state = "annuler"

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        for rec in self:
            if rec.employee_id:
                rec.department_src_id = rec.employee_id.department_id.id
