from datetime import datetime
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, AccessError, ValidationError

class FeeSchool(models.Model):
    _name = 'siantou.ems.core.fee.school'
    _description = 'Frais de scolarité'

    code = fields.Char(string="Code", required=True, index=True)
    name = fields.Char(string='Nom', required=True, index=True)
    year_id = fields.Many2one(
        'siantou.ems.core.year',
        string="Année académique",
        required=True,
        index=True,
    )

    note = fields.Html(string='Description')
    journal_id = fields.Many2one(
        'account.journal',
        string="Journal comptable",
        readonly=False,
        required=True,
        company_dependent=True,
        default=lambda self: self.env['account.journal'].sudo().search([('company_id', '=', self.env.company.id)], limit=1)
    )

    field_of_study_ids = fields.Many2many(
        'siantou.ems.core.field_of_study',
        required=True,
        string="Filières"
    )

    line_ids = fields.Many2many(
        's.e.core.fee.school.line',
        required=True,
        string="Filières"
    )

    nbre_tranche = fields.Integer(string="Nombre de tranche", required=True, default=1)
    currency_id = fields.Many2one('res.currency', string='Devise', required=True, default=lambda self: self.env.company.currency_id)
    montant_paie = fields.Monetary(string="Montant à payer", required=True, currency_field="currency_id", store=True)

    @api.constrains('journal_id')
    def _check_journal_id(self):
        for record_sudo in self.sudo():
            if record_sudo.journal_id.currency_id and record_sudo.journal_id.currency_id != record_sudo.journal_id.company_id.currency_id:
                raise ValidationError(
                    _("Journal incorrect: Le journal doit être rédigé dans la même devise que l'entreprise.")
                )

class FeeSchoolLine(models.Model):
    _name = 's.e.core.fee.school.line'
    _description = 'Gestion des élements de frais de scolarité des étudiants'
    _order = 'desc name'

    name = fields.Char(string='Nom', required=True)
    fee_school_id = fields.Many2one(
        'siantou.ems.core.fee.school',
        string="Frais de scolarité",
        required=True,
    )

    currency_id = fields.Many2one('res.currency', string='Devise', required=True, default=lambda self: self.env.company.currency_id)
    montant_paie = fields.Monetary(string="Montant à payer", required=True, currency_field="currency_id", store=True)
    date_debut = fields.Date(string="Date de début", required=True)
    date_fin = fields.Date(string="Date de fin", required=True)

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Nom déjà utilisé'),
    ]

    @api.constrains('date_debut', 'date_fin')
    def _check_date_overlap(self):
        for record in self:
            if self.search([('id', '!=', record.id), ('date_debut', '<=', record.date_fin), ('date_fin', '>=', record.date_debut),]):
                raise ValidationError('Les semestres ne peuvent se superposer')

    @api.constrains('date_debut', 'date_fin')
    def _constrains_date(self):
        for record in self:
            if record.date_debut >= record.date_fin:
                raise ValidationError('La date de fin doit être supérieure à la date de début')

