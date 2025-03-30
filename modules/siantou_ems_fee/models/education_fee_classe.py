# -*- coding: utf-8 -*-

from datetime import date
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class EducationFeeClass(models.Model):
    _name = 'siantou.ems.fee.classe'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Generation des factures par filière et niveau"

    name = fields.Char('Libellé', default="/")
    date = fields.Date('Date de génération', required=True, readonly=True)
    field_of_study_id = fields.Many2one('siantou.ems.core.field_of_study', string='Filiere', readonly=True)
    niveau = fields.Many2one('siantou.ems.core.level', string="Niveau")
    amount = fields.Monetary('Montant total de la filière', compute='_compute_amount', store=True)
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'En cours de validation'),
        ('confirm', 'Confirmer'),
        ('cancel', 'Annuler'),
    ], string='Etat', default='draft', tracking=True)

    academic_year = fields.Many2one('siantou.ems.core.year',
                                    string='Année académique',
                                    store=True)
    
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company.id, readonly=True, related_sudo=False)
    
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id, readonly=True, related_sudo=False)
    

    @api.depends('state')
    def _compute_amount(self):
        """Determine le montant total des frais pour la filière"""
        for rec in self:
            rec.amount = 0  
            total = 0
            for student in rec.field_of_study_id.student_ids:
                fees = self.env['account.move'].search([('partner_id', '=', student.partner_id.id),('academic_year_id', '=', rec.academic_year.id)])
                total += sum([x.amount_residual for x in fees])
            rec.amount = total

    
    @api.constrains("field_of_study_id", "academic_year")
    def _check_duplicated_generation(self):
        for rec in self:
            factures = self.search([('academic_year', '=', rec.academic_year.id),('field_of_study_id', '=', rec.field_of_study_id.id)])
            if len(factures) > 1:
                raise ValidationError(_("Impossible de générer pour une filière plusieurs factures sur l'année"))


    @api.model
    def create(self, valeurs):
        valeurs['name'] = 'SCOLARITE'
        return super(EducationFeeClass, self).create(valeurs)
    
    def action_draft(self):
        for rec in self:
            for student in rec.field_of_study_id.student_ids:
                fees = self.env['account.move'].search([('partner_id', '=', student.partner_id.id),('academic_year_id', '=', rec.academic_year.id)])
                for fee in fees:
                    fee.unlink()
            rec._compute_amount()
            rec.state = 'draft'
            
    def action_cancel(self):
        for rec in self:
            for student in rec.field_of_study_id.student_ids:
                fees = self.env['account.move'].search([('partner_id', '=', student.partner_id.id),('academic_year_id', '=', rec.academic_year.id)])
                for fee in fees:
                    fee.unlink()
            rec._compute_amount()
            rec.state = 'cancel'
    
    def action_validate(self):
        for rec in self:
            rec.state = 'done'

    def action_confirm(self):
        for rec in self:
            for student in rec.field_of_study_id.student_ids:
                fees = self.env['account.move'].search([('partner_id', '=', student.partner_id.id),('academic_year_id', '=', rec.academic_year.id)])
                for fee in fees:
                    fee.action_post()
                student.state = 'facture'
            rec.state = 'confirm'
    
    def generate_fees(self):
        """Generation des factures pour une scolarite normale pour la classe"""
        for rec in self:
            students = rec.field_of_study_id.student_ids.filtered(lambda x: x.state == 'draft')
            rec._student_generate_fees(students)
            rec.action_validate()

    def send_fees_mail(self):
        """Generation et envoie des factures par etudiants au parents"""
        pass

    def print_fees(self):
        """impression des factures pour la classe"""
        docids = []
        for rec in self:
            docids = rec.field_of_study_id.student_ids.ids

        return self.env.ref('siantou_ems_fee.action_fees_student').report_action(docids)
        

    def _student_generate_fees(self, students):
        """Genere les frais pour etudiants"""
        self.ensure_one()
        account_move_obj = self.env['account.move']
        structure_obj = self.env['siantou.ems.fee.structure']
        fee_category_obj = self.env['siantou.ems.fee.category']
        
        for rec in students:
            if  not self.field_of_study_id.                                                                                                                             frais:
                raise ValidationError(_('Aucun Frais disponible pour la filière'))
            
            #  Get all fees category for student
            fee_category_ids = fee_category_obj.search([])

            # Create object for invoices
            for cat in fee_category_ids:
                values = {}

                #  Get structure object for student
                annee = self.env['siantou.ems.core.year'].search(
                    [('active', '=', True)], limit=1)
                
                structure_ids = []
                
                if rec.redoublant == 'non':
                    structure_ids = structure_obj.search(
                    [('academic_year', '=', annee.id), ('fee_special', '=', False),('id', 'in', self.field_of_study_id.class_id.field_of_study_id.frais.ids),
                    ('category_id', '=', cat.id),('cycle_id', '=', self.field_of_study_id.class_id.field_of_study_id.cycle_id.id)])

                elif rec.redoublant == 'oui':
                    structure_ids = structure_obj.search(
                        [('academic_year', '=', annee.id),('is_scolarite', '=', False), ('fee_special', '=', False),('id', 'in', self.field_of_study_id.class_id.field_of_study_id.frais.ids),
                        ('category_id', '=', cat.id),('cycle_id', '=', self.field_of_study_id.class_id.field_of_study_id.cycle_id.id)])

                for struct in structure_ids:
                    lines = []
                    values = {
                        'fee_category_id': cat.id,
                        'student_id': rec.id,
                        'state': 'draft',
                        'fee_structure': struct.id,
                        'invoice_date': date.today(),
                        'class_division_id': rec.class_id.id,
                        'is_fee': True,
                        'partner_id': rec.partner_id.id,
                        'journal_id': cat.journal_id.id,
                        'move_type': 'out_invoice'
                    }
                    
                    # Records line of fee structure
                    for line in struct.fee_type_ids:
                        name = line.fee_type.product_id.description_sale
                        if not name:
                            name = line.fee_type.product_id.name
                        fee_line = {
                            'credit': line.fee_amount,
                            'partner_id': rec.partner_id.id,
                            'price_unit': line.fee_amount,
                            'price_subtotal': line.fee_amount,
                            'price_total': line.fee_amount,
                            'quantity': 1.0,
                            'product_id': line.fee_type.product_id.id,
                            'name': name,
                            'analytic_account_id': rec.class_id.class_id.analytic_id.id,
                            'account_id': cat.journal_id.default_account_id.id
                        }
                        lines.append((0, 0, fee_line))
                        fee_line2 = {
                            'debit': line.fee_amount,
                            'partner_id': rec.partner_id.id,
                            'price_unit': line.fee_amount,
                            'price_subtotal': line.fee_amount,
                            'price_total': line.fee_amount,
                            'quantity': 1.00,
                            'exclude_from_invoice_tab': True,
                            'account_id': rec.partner_id.property_account_receivable_id.id
                        }
                        lines.append((0, 0, fee_line2))
                    if struct.is_assurance and rec.assure:
                        pass
                    else:
                        values['invoice_line_ids'] = lines
                        values['line_ids'] = lines
                        move_id = account_move_obj.create(values)
        
        return True
                        