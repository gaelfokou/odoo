
from datetime import datetime, timedelta

from odoo import models, fields, api
from odoo.exceptions import ValidationError



import logging

_logger = logging.getLogger("++++++++++++")



class FeeEnrollmentWizard(models.TransientModel):
    _name = 'siantou.ems.core.fee.enrollment.student'
    _description = 'modale pour valider un paiement'

        
    name = fields.Char('Réference', default='/')
    year_id = fields.Many2one(
        'siantou.ems.core.year', 
        string='Année académique active'
    )
    student_id = fields.Many2one(
        'oe.school.student.enrollment', 
        string='Etudiant', 
        required=True)
    structure_frais_name = fields.Char(
        string='Structure de frais'
    )
    amount = fields.Monetary('Montant versé', required=True, tracking=True)
    reference = fields.Char('Réference du reçu', required=True)
    date_payment = fields.Date('Date de versement', required=True)
    currency_id = fields.Many2one(
        'res.currency', 
        default=lambda self: self.env.company.currency_id, 
        readonly=True, 
        related_sudo=False
    )




    @api.model
    def default_get(self, fields):
        res = super(FeeEnrollmentWizard, self).default_get(fields)
        if self.env.context.get('active_id'):
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
                        ('field_of_study_id','=',student_id.field_of_study_id.id),
                        ('level_id','=',student_id.level_id.id),
                        ('academic_year','=',year_id.id),
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
            #==== self.student_id is instance od student
            _logger.info(f"Student In wizard ::: {self.student_id.name}")
            _logger.info(f"Niveau In wizard ::: {self.student_id.level_id.name}")
            _logger.info(f"Niveau In wizard ::: {self.year_id.name}")
            structure_frais_id = self.env['siantou.ems.fee.structure'].sudo().search(
                [
                    ('field_of_study_id', '=',self.student_id.field_of_study_id.id),
                    ('level_id','=',self.student_id.level_id.id),
                    ('academic_year','=',self.year_id.id),
                ], 
                limit=1
            )

            journal_id = structure_frais_id.type_frais_id.category_id.journal_id
            if not journal_id:
                raise ValidationError("Le journal de paiement n'est pas configuré pour cette structure de frais")
            
            account_receivable_id = journal_id.default_account_id
            account_revenue_id = journal_id.default_account_id

            if not account_receivable_id or not account_revenue_id:
                raise ValidationError("Les comptes de créance ou de revenus ne sont pas configurés dans le journal. Veuillez vérifier la configuration")
            
            mone_vals = {
                'move_type': 'out_invoice',
                'partner_id': self.student_id.partner_id.id,
                'journal_id': journal_id.id,
                'invoice_date': fields.Date.today(),
                'invoice_date_due': fields.Date.today(),
                'ref': f"Inscription de {self.student_id.name}",
                'invoice_line_ids':[
                    (0,0,{
                        'name': f"Frais d'inscription de {self.student_id.name}",
                        'quantity': 1.0,
                        'price_unit': structure_frais_id.amount_total,
                        'account_id': account_revenue_id.id,
                    })
                ]
            }
            self.env['account.move'].create(mone_vals)


            # Créer un enregistrement de ligne de frais
            fee_payment = self.env['education.fee.payment.enrollment'].create({
                'student_id': self.student_id.id,
                'name': self.name,
                'reference': self.reference,
                'structure_frais_id':structure_frais_id.id,
                'amount': self.amount,
                'date_payment': self.date_payment
            })
            
            self.student_id.status = 'inscrip'
            _logger.info(f"montant_paie ::: {fee_payment.amount}")

            return {'type': 'ir.actions.act_window_close'}



        # #         # Créer l'écriture
        # #         move_vals = {
        # #             'date': due_date,
        # #             'journal_id': journal_id,
        # #             'line_ids': moves,
        # #             'move_type': 'out_invoice',
        # #             'ref': f'inscription: {fee_student.student_id.name}',
        # #         }
        # #         move = self.env['account.move'].create(move_vals)
        # #         move.action_post()  # Publiez le mouvement
        # #         return True
         
        # for rec in self:
        #     if rec.student_id:
        #         # Générer le numéro de dossier
        #         dossier_number = self.generate_dossier_number()
                
        #         # Générer le nom d'utilisateur et le mot de passe de l'étudiant
        #         username = rec.student_id.email  # Utilisez l'email comme nom d'utilisateur, par exemple
        #         password = self.env['res.users'].generate_password()  # Fonction pour générer un mot de passe sécurisé
                
        #         # Créer un enregistrement de ligne de frais
        #         fee_student = self.env['siantou.ems.core.fee.student'].create({
        #             'student_id': rec.student_id.id,
        #             'fee_enroll_struct_id': rec.fee_enroll_struct_id.id,
        #             'date_paiement': fields.Date.today()
        #         })
                
        #         # Récupérer le journal et ses comptes configurés
        #         journal = rec.fee_enroll_struct_id.journal_id
        #         if not journal:
        #             raise ValidationError("Le journal de paiement n'est pas configuré pour cette structure de frais.")
                
        #         # Utiliser les comptes configurés dans le journal
        #         account_receivable = journal.default_account_id  # Compte de créance client configuré dans le journal
        #         account_revenue = journal.default_account_id  # Compte de revenus configuré dans le journal
                
        #         if not account_receivable or not account_revenue:
        #             raise ValidationError("Les comptes de créance ou de revenus ne sont pas configurés dans le journal. Veuillez vérifier la configuration.")
                
        #         # Mise à jour du statut de l'étudiant
        #         rec.student_id.status = 'inscrip'
        #         due_date = fields.Date.today() + timedelta(days=30)
                
        #         # Création de la facture avec les lignes d'écriture
        #         move_vals = {
        #             'move_type': 'out_invoice',
        #             'partner_id': rec.student_id.partner_id.id,
        #             'journal_id': journal.id,
        #             'invoice_date': fields.Date.today(),
        #             'invoice_date_due': due_date,
        #             'ref': f'Inscription: {rec.student_id.name}',
        #             'invoice_line_ids': [(0, 0, {
        #                 'name': f"Frais d'inscription pour {rec.student_id.name}",
        #                 'quantity': 1,
        #                 'price_unit': rec.fee_enroll_struct_id.montant_paie,
        #                 'account_id': account_revenue.id,  # Compte de revenu du journal
        #             })],
        #         }
                
        #         move = self.env['account.move'].create(move_vals)
        #         move.action_post()
                
        #         # Envoyer l'email avec le numéro de dossier
        #         rec.action_send_email(rec.student_id, dossier_number, username, password)