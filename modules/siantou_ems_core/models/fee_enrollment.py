from datetime import datetime
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, AccessError, ValidationError




class FeeEnrollment(models.Model):
    _name = 'siantou.ems.core.fee.enrollment'
    _description = "Gestion des Frais d'inscription"

    code = fields.Char(string="Code", required=True, index=True,)
    name = fields.Char(string="Nom", required=True, index=True,)
    year = fields.Many2one(
        'siantou.ems.core.year',
        string="Année académique", 
        required=True, index=True,
    )
    company_id = fields.Many2one('res.company', 
        string='Université', index=True,
        default=lambda self: self.env.company,
        domain=[('active','=',True),('is_school','=',True)]
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
    level_ids = fields.Many2many(
        'siantou.ems.core.level', 
        required=True,
        string="Niveaux"
    )
    montant_paie = fields.Monetary(string="Montant à payer", required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id)
    active = fields.Boolean(string="Actif", default=False)


    @api.constrains('journal_id')
    def _check_journal_id(self):
        for record_sudo in self.sudo():
            if record_sudo.journal_id.currency_id and record_sudo.journal_id.currency_id != record_sudo.journal_id.company_id.currency_id:
                raise ValidationError(
                    _("Journal incorrect: Le journal doit être rédigé dans la même devise que l'entreprise.")
                )

    # Contrainte logique pour empêcher d'avoir plusieurs structure de frais d'inscritption actives simultannément
    @api.constrains('active')
    def _check_unique_active(self):
        for record in self:
            if self.search([('id', '!=', record.id), ('active', '=', 'True')]):
                raise ValidationError("Il ne peut y avoir qu'une seule structure de frais d'inscription active à la fois.")


class FeeEnrollStudent(models.Model):
    _name = 'siantou.ems.core.fee.student'
    _description = "Gestion des Frais d'inscription des étudiants"
    _order = 'name'

    fee_enroll_struct_id = fields.Many2one(
        'siantou.ems.core.fee.enrollment', 
        string="Frais de préinscription", 
        required=True,  
    )

    student_id = fields.Many2one(
        'oe.school.student.enrollment', 
        string="Étudiant", 
        ondelete='cascade',
        required=True,    
    )
    date_paiement = fields.Date(string="Date de paiement", required=True)