# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _

from odoo.exceptions import UserError


class EncaissementFraisEtudiant(models.TransientModel):
    _name = 'encaissement.frais.etudiant.wizard'

    recherche_etudiant_nom = fields.Char("Nom de l'étudiant")
    recherche_etudiant_date_naissance = fields.Date("Date de naissance de l'étudiant")
    recherche_etudiant_matricule= fields.Char("Matricule de l'étudiant")
    etudiant_id = fields.Many2one('oe.school.student', 'Etudiant')
    caisse_id = fields.Many2one('account.bank.statement', 'Caisse')
    montant_recu = fields.Monetary("Montant reçu")
    montant_paye = fields.Monetary("Montant payé")
    montant_a_rembourser = fields.Monetary("Montant à rembourser", compute='_compute_montant_a_rembourser')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id)
    etat_de_progression = fields.Selection([
        ('recherche_etudiant', "Recherche de l'étudiant"),
        ('validation_etudiant', "Validation de l'étudiant"),
        ('saisir_les_montants', "Saisir les montants")
    ], default='recherche_etudiant')
    filiere_id = fields.Many2one('siantou.ems.core.field_of_study', related='etudiant_id.field_of_study_id')
    specialite_id = fields.Many2one('siantou.ems.core.specialty', related='etudiant_id.specialty_id')
    cycle_id = fields.Many2one('oe.school.course', related='etudiant_id.cycle_id')
    niveau_id = fields.Many2one('siantou.ems.core.level', related='etudiant_id.level_id')

    @api.constrains('recherche_etudiant_nom', 'recherche_etudiant_matricule')
    def _check_recherche_etudiant(self):
        for rec in self:
            if len(rec.recherche_etudiant_nom or '') < 3 and rec.etat_de_progression == 'validation_etudiant':
                raise exceptions.ValidationError(_("Le nom de l'étudiant doit avoir au moins 3 caractères"))
            if len(rec.recherche_etudiant_matricule or '') < 3 and rec.etat_de_progression == 'validation_etudiant':
                raise exceptions.ValidationError(_("Le matricule de l'étudiant doit avoir au moins 3 caractères"))

    @api.depends('montant_recu', 'montant_paye')
    def _compute_montant_a_rembourser(self):
        for rec in self:
            rec.montant_a_rembourser = rec.montant_recu - rec.montant_paye


    def action_verification_precedent(self):
        self.write({
            'etudiant_id': False,
            'recherche_etudiant_nom': False,
            'recherche_etudiant_date_naissance': False,
            'recherche_etudiant_matricule': False,
            'etat_de_progression': 'recherche_etudiant',
        })


    def action_encaisser_precedent(self):
        self.write({
            'etat_de_progression': 'validation_etudiant',
        })

        return {
            'type': 'ir.actions.act_window',
            'name': "Encaissement > Recherche Etudiant(e)",
            'res_model': 'encaissement.frais.etudiant.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    def action_continuer(self):
        etudiant = self.env['oe.school.student'].search([
            ('name', 'ilike', self.recherche_etudiant_nom),
            '|',
            ('matricule', 'ilike', self.recherche_etudiant_matricule),
            ('date_naissance', '=', self.recherche_etudiant_date_naissance),
        ], limit=1)
        if not etudiant:
            raise UserError(_("Erreur ! Aucun étudiant n'a été trouvé"))
        self.write({
            'etudiant_id': etudiant.id,
            'recherche_etudiant_matricule': etudiant.id,
            'recherche_etudiant_date_naissance': etudiant.date_naissance,
            'etat_de_progression': 'validation_etudiant',
        })
        return {
            'type': 'ir.actions.act_window',
            'name': "Encaissement > Vérification Etudiant(e)",
            'res_model': 'encaissement.frais.etudiant.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    def action_valider(self):
        self.write({
            'etat_de_progression': 'saisir_les_montants',
        })
        return {
            'type': 'ir.actions.act_window',
            'name': "Encaissement > Saisie des montants (%s)" % self.etudiant_id.display_name,
            'res_model': 'encaissement.frais.etudiant.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    def action_encaisser(self):
        transaction_vals = self._prepare_transaction_vals()
        self.caisse_id.write({'line_ids': [(0, 0, transaction_vals)]})
        return True

    def _prepare_transaction_vals(self):
        return {
            # Overidden from self.sheet_id._prepare_transaction_vals() so we can use the expense date for the account move date
            'payment_ref': "Encaissement des frais de scolarité",
            # 'ecole_id': self.sheet_id.ecole_id.id,
            'filiere_id': self.etudiant_id.field_of_study_id.id,
            'specialite_id': self.etudiant_id.specialty_id.id,
            # 'annee_academique_id': self.etudiant_id.annee_academique_id.id,
            'cycle_id': self.etudiant_id.cycle_id.id,
            'partner_id': self.etudiant_id.partner_id.id,
            'amount': self.montant_paye,
            'montant_recu': self.montant_recu,
            'currency_id': self.currency_id.id,
        }
        # Création de la transaction

    @api.constrains('montant_recu', 'montant_paye')
    def check_montants(self):
        if self.montant_recu < self.montant_paye:
            raise UserError(_("Erreur ! Le montant versé ne peut pas être inférieur au montant payé"))