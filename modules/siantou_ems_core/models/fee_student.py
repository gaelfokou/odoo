from datetime import datetime
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, AccessError, ValidationError


class FeeStruct(models.Model):
    _name = 'siantou.ems.core.fee.struct'
    _description = 'Structuration des frais de scolarité'

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string='Nom', required=True)
    is_active = fields.Boolean(string='Actif ?', default=True)
    company_id = fields.Many2one('res.company',
        string='Université', index=True,
        default=lambda self: self.env.company,
        domain=[('active', '=', True),('is_university', '=', True)]
    )

    note = fields.Html(string='Description')
    journal_id = fields.Many2one(
        'account.journal',
        string="Journal comptable",
        readonly=False, required=True,
        company_dependent=True,
        default=lambda self: self.env['account.journal'].sudo().search([('company_id', '=', self.env.company.id)], limit=1)
    )
    # cycle_ids = fields.One2many(
    #     'oe.school.course',
    #     'fee_struct_id',
    #     # required=True
    # )
    # fee_line_ids = fields.One2many(
    #     'siantou.ems.core.fee.struct.line',
    #     'fee_struct_id',
    #     string="Lignes"
    # )
    # nbre_tranche = fields.Integer(string="Nombre de tranche")
    # type_fee = fields.Selection([
    #         ('paie_tranch', 'Paiement par tranche'),
    #         ('paie_total', 'Paiement total')
    #     ],
    #     string="Type de paiement",
    #     required=True
    # )
    montant_paie_total = fields.Integer(string="Montant à payer")

    @api.constrains('journal_id')
    def _check_journal_id(self):
        for record_sudo in self.sudo():
            if record_sudo.journal_id.currency_id and record_sudo.journal_id.currency_id != record_sudo.journal_id.company_id.currency_id:
                raise ValidationError(
                    _("Journal incorrect: Le journal doit être rédigé dans la même devise que l'entreprise.")
                )

# class FeeLine(models.Model):
#     _name = 'siantou.ems.core.fee.struct.line'
#     _description = 'Ligne des frais de scolarité'
#     _order = 'name'

#     name = fields.Char(string='Nom', required=True)
#     montant_paie = fields.Integer(string="Montant")
#     date_created = fields.Date(string="Date de création", default=datetime.now())
#     fee_struct_id = fields.Many2one(
#         'siantou.ems.core.fee.struct',
#         string="Structure des frais",
#         # required=True,
#     )

#     _sql_constraints = [
#         ('unique_name', 'unique(name)', 'Nom déjà utilisé'),
#         ('unique_date_paie', 'unique(date_paie)', 'Date butoire déjà utilisé'),
#     ]

#     @api.constrains('date_paie')
#     def _check_date_overlap(self):
#         for record in self:
#             if self.search([('id', '!=', record.id), ('date_paie', '=', record.date_paie), ('date_paie', '>=', record.date_paie),]):
#                 raise ValidationError('Entrer une date supérieur')


class FeeStudent(models.Model):
    _name = 'siantou.ems.core.fee.student'
    _description = 'Frais de d\'inscription des étudiants'

    fee_enroll_struct_id = fields.Many2one(
        'siantou.ems.core.fee.enrollment',
        string="Frais d'incription",
        required=True,
    )

    student_id = fields.Many2one(
        'oe.school.student.enrollment',
        string="Étudiant",
        ondelete='cascade',
        required=True,
    )

    date_paiement = fields.Date(string="Date de paiement", required=True)

