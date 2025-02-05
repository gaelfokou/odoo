from datetime import datetime

from odoo import fields, models, api
from odoo.tools import formatLang


class AccountBankStatementLine (models.Model):
    _inherit = 'account.bank.statement.line'

    journal_entry_ids = fields.One2many('account.move.line', 'statement_line_id', 'Journal Items', copy=False,
                                        readonly=True)

    bank_account_id = fields.Many2one('res.partner.bank', string='Bank Account')
    date = fields.Date(related='statement_id.date', readonly=False)
    type_inclusion_fee = fields.Selection(
        [
            ('fee_inscrip', "Frais d'inscription"),
            ('fee_scol', 'Frais de scolarité'),
            ('fee_spec', 'Frais spéciaux'), 
        ],
        "Catégorie de frais", 
        # required=True,
    )
    ecole_id = fields.Many2one('siantou.ems.core.school', string='École')
    departement_id = fields.Many2one('hr.department', string='Département')
    filiere_id = fields.Many2one('siantou.ems.core.field_of_study', string='Filière')
    specialite_id = fields.Many2one('siantou.ems.core.specialty', string='Spécialité')
    annee_academique_id = fields.Many2one('siantou.ems.core.year', string='Année académique')
    cycle_id = fields.Many2one('oe.school.course', string='Cycle')
    niveau_id = fields.Many2one('siantou.ems.core.level', string='Niveau')
    semestre_id = fields.Many2one('siantou.ems.core.year.semester', string='Semestre')

    def _get_annee_academique_courante(self):
        return self.env['siantou.ems.core.year'].search([('active', '=', True)], limit=1).name

    def imprimer_recu(self):
        for rec in self:
            pass
            data = {}

            enrollement = self.env['oe.school.student.enrollment'].search([('partner_id', '=', rec.partner_id.id)], limit=1)
            annee_academique = enrollement.annee_acad
            if not enrollement.annee_acad:
                annee_academique = rec._get_annee_academique_courante()

            data['info_etudiant'] = {
                'nom': rec.partner_id.display_name,
                'filiere': "%s / %s" % (enrollement.field_of_study_id.name, enrollement.specialty_id.name),
                'matricule': enrollement.matricule,
                'niveau': enrollement.level_id.name,
            }

            data['info_entete'] = {
                'anne_academique': annee_academique,
                'date': rec.date,
                'numero_recu': rec.move_id.name,
                'montant_verse': formatLang(self.env, rec.amount, currency_obj=rec.currency_id),
            }

            data['lignes_de_recouvrements'] = []
            redevances = self.env['account.move'].search([('move_type', '=', 'out_invoice'), ('payment_state', 'in', ['paid', 'partial'])])
            for redevance in redevances:
                if not redevance.invoice_payments_widget:
                    continue
                info_sur_paiements = redevance.invoice_payments_widget['content'][0]
                if rec.move_id.id == info_sur_paiements['move_id']:
                    info_ligne = {
                        'code': "#",
                        'libelle': redevance.ref,
                        'montant_recu': info_sur_paiements['amount_company_currency'],
                        'observation': "Observation",
                    }
                    data['lignes_de_recouvrements'].append(info_ligne)

            report_action = self.env.ref('account_cash_bank_management.action_report_student_core_pdf')
            # return report_action.report_action(self,data=data)
            return report_action.report_action(self,data=data)

    @api.model
    def create(self, vals):
        if 'statement_id' in vals:
            statement = self.env['account.bank.statement'].browse(vals.get('statement_id'))
            vals['date'] = statement.date
            return super(AccountBankStatementLine, self).create(vals)
        else:
            if vals.get('date'):
                _date = vals.get('date')
            elif self.date:
                _date = self.date
            else:
                _date = datetime.now()
            statement = self.env['account.bank.statement'].search([
                ('journal_id', '=', vals.get('journal_id')),
                ('date', '=', _date)
            ], limit=1)

        if not statement:
            statement = self.env['account.bank.statement'].create({
                'journal_id': vals.get('journal_id'),
                'date': _date,
                'state': 'open',
            })

        vals['statement_id'] = statement.id
        vals['date'] = statement.date

        return super(AccountBankStatementLine, self).create(vals)

    @api.depends('date', 'sequence')
    def _compute_internal_index(self):
        for rec in self:
            if not rec.date:
                rec.date = rec.statement_id.date
        return super()._compute_internal_index()

