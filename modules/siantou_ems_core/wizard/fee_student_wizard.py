
from datetime import datetime, timedelta

from odoo import models, fields, api, Command, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import clean_context


import logging

_logger = logging.getLogger(__name__)



class FeeEnrollmentWizard(models.TransientModel):
    _name = 'siantou.ems.core.fee.enrollment.student'
    _description = 'modale pour valider un paiement'

        
    name = fields.Char('Réference du paiement', default='/')
    year_id = fields.Many2one(
        'siantou.ems.core.year', 
        string='Année académique active'
    )
    student_id = fields.Many2one(
        'oe.school.student.enrollment', 
        string='Étudiant', 
        required=True
    )
    student_name = fields.Char(
        string='Nom du déposant',
        related='student_id.name'
    )
    student_phone = fields.Char(
        string='Téléphone du déposant',
        related='student_id.num_tel'
    )
    structure_frais_name = fields.Char(
        string='Structure de frais'
    )
    amount = fields.Monetary(
        'Montant versé', 
        required=True, 
        tracking=True
    )
    cash_register_id = fields.Many2one(
        'account.journal',
        string='caisse',
        required=True
    )
    # caisse_domain = fields.Binary()
    # reference = fields.Char('Réference du reçu', required=True)
    mode_payment = fields.Selection(
        [
            ('bank', 'Virement bancaire'),
            ('cash', 'Paiement en espèce(Cash)')
        ],
        string='Mode de paiement', 
        # default="cash",
        required=True
    )
    # cni = fields.Char(string="Numéro CNI", required=True)
    # date_delivr_cni = fields.Date(
    #     string="Date de délivrance", 
    #     required=True
    # )
    # lieu_delivr_cni = fields.Char(
    #     string="Lieu de délivrance", 
    #     required=True
    # )
    # titulaire_compte = fields.Char(string="Titulaire du compte")
    # numero_compte = fields.Char(string="N° de compte")
    # name_bank = fields.Char(string="Nom bank",)
    # code_guichet = fields.Char(string="Code guichet")
    date_payment = fields.Date('Date de versement', 
        required=True, 
        default=fields.Date.context_today
    )
    currency_id = fields.Many2one(
        'res.currency', 
        default=lambda self: self.env.company.currency_id, 
        readonly=True, 
        related_sudo=False
    )


    # @api.onchange('mode_payment')
    # def onchange_mode_payment(self):
    #     for rec in self:

    #         journals = self.env['account.journal'].search(
    #             [('type','=',rec.mode_payment)], 
    #         )
    #         _logger.info(journals)
    #         rec.caisse_id = [(0,0,journals)]




    @api.model
    def default_get(self, fields):
        res = super(FeeEnrollmentWizard, self).default_get(fields)
        if self.env.context.get('active_id'):
            enrol_payments = self.env['education.fee.payment.enrollment'].search([])
            res['student_id'] = self.env.context.get('active_id')
            year_id = self.env['siantou.ems.core.year'].search(
                [('active', '=',True),], 
                limit=1
            )
            student_id = self.env['oe.school.student.enrollment'].search(
                [('id', '=',int(res['student_id'])),], 
                limit=1
            )
            try:
                structure_frais_id = self.env['siantou.ems.fee.structure'].search(
                    [
                        ('field_of_study_ids','in',student_id.field_of_study_id.id),
                        ('level_id','=',student_id.level_id.id),
                        ('type_paiement','=','pu'),
                        ('type_inclusion_fee','=','fee_inscrip'),
                        ('academic_year','=',year_id.id),
                        ('state','=', 'validate'),
                    ], 
                    limit=1
                )
            except Exception as e:
                raise ValidationError(e.args)

            if not year_id:
                raise ValidationError(f"Aucune année active trouvé")
            
            if not structure_frais_id:
                raise ValidationError(f"Aucune structure de frais de paiement disponible pour {student_id.field_of_study_id.name} {student_id.level_id.name} pour l'année {year_id.name}")
            
            # _logger.info(student_id)
            # _logger.info(structure_frais_id)
            # _logger.info(res['student_id'])
            # _logger.info(res)
            res['name'] = f"INS000{len(enrol_payments)+1}"
            res['year_id'] = year_id.id
            res['amount'] = structure_frais_id.amount_total
            res['structure_frais_name'] = structure_frais_id.fee_structure_name
        return res


    # def action_send_email(self, student_id, dossier_number):
    #     template = self.env.ref('siantou_ems_core.email_template_preinscription')  # Référence à votre template d'email
    #     template.with_context(dossier_number=dossier_number).send_mail(student_id.id, force_send=True)
    

    def action_send_email(self, student, dossier_number, username, password):
        # Condition pour les étudiants en licence ou master
        if student.niveau in ['Licence', 'Master']:
            template_id = self.env.ref('siantou_ems_core.email_template_preinscription_conditionnelle').id
        else:
            template_id = self.env.ref('siantou_ems_core.email_template_preinscription_standard').id
        
        template = self.env['mail.template'].browse(template_id)
        template.with_context(
            dossier_number=dossier_number,
            username=username,
            password=password
        ).send_mail(student.id, force_send=True)


    def generate_dossier_number(self):
        """ Génère un numéro de dossier unique basé sur le modèle 'Dossier-<ID>' """
        return f'Dossier-{self.env["ir.sequence"].next_by_code("preinscription.dossier") or self.id}'


    def enroll_student(self):
        if self.student_id:
            journal_id = self.cash_register_id
            if not journal_id:
                raise ValidationError("Le journal de paiement n'est pas configuré pour cette structure de frais")

            account_receivable_id = journal_id.default_account_id
            account_revenue_id = journal_id.default_account_id
            # _logger.info(account_revenue_id)
            if not account_receivable_id or not account_revenue_id:
                raise ValidationError("Les comptes de créance ou de revenus ne sont pas configurés dans le journal. Veuillez vérifier la configuration")            

            mone_vals = {
                'move_type': 'out_invoice',
                'partner_id': self.student_id.partner_id.id,
                'journal_id': journal_id.id,
                'invoice_date': fields.Date.today(),
                'invoice_date_due': fields.Date.today(),
                'annee_academique_id': self.student_id.year_id.id,
                'niveau_id': self.student_id.level_id.id,
                'filiere_id': self.student_id.field_of_study_id.id,
                'cycle_id': self.student_id.cycle_id.id,
                'ecole_id': self.student_id.field_of_study_id.school_id.id,
                'specialite_id': self.student_id.specialty_id.id,
                'ref': f"Inscription de {self.student_id.name}",
                'invoice_line_ids':[
                    (0,0,{
                        'name': f"Frais d'inscription de {self.student_id.name}",
                        'quantity': 1.0,
                        'price_unit': self.amount,
                        'account_id': account_revenue_id.id,
                    })
                ]
            }
            account_move_id = self.env['account.move'].create(mone_vals)
            account_move_id.action_post()

            self.student_id.status = 'inscrip'

            return {'type': 'ir.actions.act_window_close'}
            
            # self._do_create_and_post_moves()
            # return {
            #     'type': 'ir.actions.client',
            #     'tag': 'display_notification',
            #     'params': {
            #         'type': 'success',
            #         'message': "Récupération des données réussis",
            #         'next': {'type': 'ir.actions.act_window_close'},
            #     }
            # }


    #============ Part 1: prepare vals des transactions
    def _prepare_transaction_vals(self):  
        self.ensure_one()  
        journal = self.cash_register_id  
        payment_method_line = self.cash_register_id.inbound_payment_method_line_ids[0].payment_method_id
        statement = self.env['account.bank.statement'].search([  
            ('date', '=', self.date_payment),  
            ('create_uid', '=', self.env.user.id),  
            ('state', '=', 'open'),  
            ('journal_id', '=', journal.id)  
        ], limit=1)  
        if not statement:  
            raise ValidationError(_("Vous devez ouvrir une caisse ou un brouillard de banque à la date du %s pour enregistrer le décaissement", self.date_payment))  
        if not payment_method_line:  
            raise ValidationError(_("Vous avez manqué d'ajouter une méthode de paiement manuel au niveau du journal (%s)", journal.name))  
        
        return {  
            #**self.sheet_id._prepare_move_vals(),  
            'date': self.date_payment,  # Overidden from self.sheet_id._prepare_transaction_vals() so we can use the expense date for the account move date  
            'payment_ref': "Frais d'inscription de %s" % self.student_id.name,
            'ref': "Frais d'inscription de %s" % self.student_id.name,
            'ecole_id': self.student_id.field_of_study_id.school_id.id,  
            'departement_id': self.student_id.field_of_study_id.department_id.id,  
            'filiere_id': self.student_id.field_of_study_id.id,  
            'specialite_id': self.student_id.specialty_id.id,  
            'annee_academique_id': self.year_id.id,  
            'cycle_id': self.student_id.field_of_study_id.cursus_id.id,
            'partner_id': self.student_id.partner_id.id,
            'journal_id': journal.id,  
            # 'expense_sheet_id': self.sheet_id.id,  
            # 'statement_id': statement.id,  
            'amount': self.amount,  
            'currency_id': self.currency_id.id,
        }
 
 
    #======================= Part 2: Comptabilisation des pièces comptables des transactions
    def _do_create_and_post_moves(self):  
        self = self.with_context(clean_context(self.env.context))  # remove default_*  
        # skip_context = {  
        #     'skip_invoice_sync': True,  
        #     'skip_invoice_line_sync': True,  
        #     'skip_account_move_synchronization': True,  
        # }  
        # own_account_sheets = self.filtered(lambda sheet: sheet.payment_mode == 'own_account')  
        # company_account_sheets = self - own_account_sheets  
        transaction = self.env['account.bank.statement.line'].create(self._prepare_transaction_vals())
        # Set the main attachment on the moves directly to avoid recomputing the  
        # `register_as_main_attachment` on the moves which triggers the OCR again    
        # for move in moves:  
        #     move.message_main_attachment_id = move.attachment_ids[0] if move.attachment_ids else None  
        # for expense in company_account_sheets.expense_line_ids: 
        #     transaction = self.env['account.bank.statement.line'].create(expense._prepare_transaction_vals())  
        #     debit_move_line = transaction.move_id.line_ids[1]
        #     debit_move_line.write({'account_id': expense.account_id.id, 'name': expense.name})  
        #     transaction.move_id.button_draft()
        #     moves |= transaction.move_id
        transaction.move_id.button_draft()
        transaction.move_id.action_post()
        # self.activity_update()
        return transaction.move_id
 




