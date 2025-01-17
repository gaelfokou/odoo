
from datetime import datetime, timedelta

from odoo import models, fields, api
from odoo.exceptions import ValidationError



import logging

_logger = logging.getLogger("++++++++++++")



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
        string='Etudiant', 
        required=True)
    structure_frais_name = fields.Char(
        string='Structure de frais'
    )
    amount = fields.Monetary('Montant versé', required=True, tracking=True)
    reference = fields.Char('Réference du reçu', required=True)
    date_payment = fields.Date('Date de versement', required=True, default=fields.Date.context_today)
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
            #==== self.student_id is instance od student
            _logger.info(f"Student In wizard ::: {self.student_id.name}")
            _logger.info(f"Niveau In wizard ::: {self.student_id.level_id.name}")
            _logger.info(f"Niveau In wizard ::: {self.year_id.name}")
            structure_frais_inscript_id = self.env['siantou.ems.fee.structure'].sudo().search(
                [
                    ('field_of_study_ids','in',self.student_id.field_of_study_id.id),
                    ('level_id','=',self.student_id.level_id.id),
                    ('type_paiement','=','pu'),
                    ('type_inclusion_fee','=','fee_inscrip'),
                    ('academic_year','=',self.year_id.id),
                ], 
                limit=1
            )

            journal_id = structure_frais_inscript_id.type_frais_id.category_id.journal_id
            if not journal_id:
                raise ValidationError("Le journal de paiement n'est pas configuré pour cette structure de frais")
            
            account_receivable_id = journal_id.default_account_id
            account_revenue_id = journal_id.default_account_id

            if not account_receivable_id or not account_revenue_id:
                raise ValidationError("Les comptes de créance ou de revenus ne sont pas configurés dans le journal. Veuillez vérifier la configuration")
            
            amount_rest = self.amount-structure_frais_inscript_id.amount_total
            price_unit = 0.0

            if amount_rest <0:
                raise ValidationError(f"Les frais d'inscription de la filière {self.student_id.field_of_study_id.name} {self.student_id.level_id.name} s'élève à {structure_frais_inscript_id.amount_total}")

            
            if amount_rest==0:
                # Créer un enregistrement de ligne de frais
                self.env['education.fee.payment.enrollment'].create({
                    'student_id': self.student_id.id,
                    'name': self.name,
                    'reference': self.reference,
                    'structure_frais_id': structure_frais_inscript_id.id,
                    'amount': self.amount or structure_frais_inscript_id.amount_total,
                    'amount_plus': 0.0,
                    'amount_moins': 0.0,
                    'status': 'all',
                    'date_payment': self.date_payment
                })
                price_unit = self.amount
            
            if amount_rest>0:
                # Créer un enregistrement de ligne de frais
                self.env['education.fee.payment.enrollment'].create({
                    'student_id': self.student_id.id,
                    'name': self.name,
                    'reference': self.reference,
                    'structure_frais_id': structure_frais_inscript_id.id,
                    'amount': structure_frais_inscript_id.amount_total,
                    'amount_plus': amount_rest,
                    'amount_moins': 0.0,
                    'status': 'all',
                    'date_payment': self.date_payment
                })
                price_unit = structure_frais_inscript_id.amount_total

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
                        'price_unit': price_unit,
                        'account_id': account_revenue_id.id,
                    })
                ]
            }
            self.env['account.move'].create(mone_vals)

            self.student_id.status = 'inscrip'

            return {'type': 'ir.actions.act_window_close'}






























            


