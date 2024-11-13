
from datetime import datetime, timedelta

from odoo import models, fields, api
from odoo.exceptions import ValidationError



import logging

_logger = logging.getLogger("++++++++++++")



class FeeEnrollmentWizard(models.TransientModel):
    _name = 'siantou.ems.core.fee.enrollment.student'
    _description = 'modale pour valider un paiement'

    student_id = fields.Many2one(
        'oe.school.student.enrollment', 
        string="Etudiant concerné",
    )
    fee_enroll_struct_id = fields.Many2one(
        'siantou.ems.core.fee.enrollment', 
        string="Frais de préinscription", 
        # required=True,
        default=lambda self: self.env['siantou.ems.core.fee.enrollment'].sudo().search([('active', '=',True)], limit=1)  
    )
    
    montant_paie = fields.Integer(
        string="Montant de paiement", 
    )


    @api.model
    def default_get(self, fields):
        res = super(FeeEnrollmentWizard, self).default_get(fields)
        fee_enroll = self.env['siantou.ems.core.fee.enrollment'].sudo().search([('active', '=',True)], limit=1)  
        if self.env.context.get('active_id'):
            res['student_id'] = self.env.context.get('active_id')
            res['montant_paie'] = fee_enroll.montant_paie
        return res


    # @api.onchange('fee_enroll_struct_id')
    # def _onchange_fee_enroll_struct_id(self):
    #     if self.fee_enroll_struct_id:
    #         # Get the first fee line associated with the selected fee structure
    #         fee_lines = self.env['siantou.ems.core.fee.struct.line'].search([
    #             ('fee_enroll_struct_id', '=', self.fee_enroll_struct_id.id)
    #         ], limit=1)

    #         if fee_lines:
    #             self.fee_struct_line_id = fee_lines.id
    #         else:
    #             self.fee_struct_line_id = False


    def enroll_student(self):
        if self.student_id:
            #==== self.student_id is instance od student
            _logger.info(f"Student In wizard ::: {self.student_id.name}")
            _logger.info(f"Niveau In wizard ::: {self.student_id.level_id.name}")
            
            # Créer un enregistrement de ligne de frais
            fee_student = self.env['siantou.ems.core.fee.student'].create({
                'student_id': self.student_id.id,
                'fee_enroll_struct_id': self.fee_enroll_struct_id.id,
                'date_paiement': fields.Date.today()
            })
            
            self.student_id.status = 'inscrip'
            _logger.info(f"montant_paie ::: {fee_student.fee_enroll_struct_id.montant_paie}")
            # Supposons que la date d'échéance soit 30 jours après la date de facture
            due_date = datetime.now() + timedelta(days=30)
            move = self.env['account.move'].create({
                'move_type': 'out_invoice',  # ===== On informe la comptabilité que nous avons vendu une place
                'partner_id': fee_student.student_id.partner_id.id,
                'journal_id': fee_student.fee_enroll_struct_id.journal_id.id,  # En supposant que l'identifiant journal_id existe dans la structure tarifaire
                'invoice_date_due': due_date,  # Ajout de la date d'échéance ici
                'line_ids': [
                    (0, 0, {
                        'name': f'Paiement de {fee_student.student_id.name}',
                        'partner_id': fee_student.student_id.partner_id.id,
                        'account_id': fee_student.fee_enroll_struct_id.journal_id.default_account_id.id,  # S'assurer de l'existence du compte
                        'debit': fee_student.fee_enroll_struct_id.montant_paie,
                        'credit': 0.0,
                        'date': due_date,  # Date d'échéance au niveau de la ligne
                    }),
                    (0, 0, {
                        'name': 'Revenue',
                        'partner_id': fee_student.student_id.partner_id.id,
                        'account_id': fee_student.fee_enroll_struct_id.journal_id.default_account_id.id,  # S'assurer de l'existence du compte
                        'debit': 0.0,
                        'credit': fee_student.fee_enroll_struct_id.montant_paie,
                        'date': due_date,  # Date d'échéance au niveau de la ligne
                    }),
                ],
            })

            #Après le déménagement
            move.action_post()

            return {'type': 'ir.actions.act_window_close'}



