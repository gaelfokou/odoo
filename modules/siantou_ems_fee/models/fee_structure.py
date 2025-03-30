# -*- coding: utf-8 -*-


from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime
import logging


_logger = logging.getLogger(__name__)



class FeeStructure(models.Model):
    _name = 'siantou.ems.fee.structure'
    _rec_name = 'fee_structure_name'


    _sql_constraints = [
        ('unique_fee_structure_name', 'unique(fee_structure_name)', 'Ce libellé existe déjà'),
    ]


    @api.depends('fee_type_ids.fee_amount')
    def compute_total(self):
        for rec in self:
            rec.amount_total = sum(line.fee_amount for line in rec.fee_type_ids)


    company_currency_id = fields.Many2one(
        'res.currency', compute='get_company_id', readonly=True, related_sudo=False)
    fee_structure_name = fields.Char('Libellé', compute='_compute_fee_structure_name',store=True)
    comment = fields.Text('Information additionnel')
    academic_year = fields.Many2one(
        'siantou.ems.core.year', string='Année académique', required=True)
    # expire = fields.Boolean('Expire', default=False)
    amount_total = fields.Float(
        'Montant', currency_field='company_currency_id', required=True)
    type_frais_id = fields.Many2one(
        'siantou.ems.fee.type', 
        string='Type de frais', 
        required=True
    )
    school_id = fields.Many2one('siantou.ems.core.school', required=False,string='Ecole')
    field_of_study_ids = fields.Many2many('siantou.ems.core.field_of_study', required=True,string='Filières')
    level_id = fields.Many2one('siantou.ems.core.level', required=True,string='Niveau')
    type_paiement = fields.Selection(
        [
            ('pu', 'Paiement unique'), 
            ('pt', 'Paiement par tranches'),
        ],
        'Type de paiement', 
        required=True,
        default='pu',
    )
    type_inclusion_fee = fields.Selection(
        [
            ('fee_inscrip', "Inclure dans les frais d'inscription"),
            ('fee_scol', 'Inclure dans les frais de scolarité'),
            ('fee_spec', 'Inclure dans les frais spéciaux'), 
        ],
        "Visibilité de la structure de frais", 
        required=True,
        default='fee_inscrip',
    )
    fee_type_ids = fields.One2many(
        'siantou.ems.fee.structure.lines', 
        'fee_structure_id', 
        string='Liste des tranches de paiement',
        # compute='_create_tranche',
        # store=True,
    )
    nbre_tranche = fields.Integer("Nombre de tranches", required=True, default=1,)
    sequence = fields.Integer('Priorité', default=1, required=True, store=True)
    active = fields.Boolean(default=True)
    state = fields.Selection([
            ('no_create', 'Encours de création'),
            ('create', 'En attente de validation'),
            ('validate', 'Validé'),
        ],
        default='no_create'
    )


    @api.depends('level_id', 'type_frais_id', 'type_paiement', 'academic_year', 'field_of_study_ids', 'school_id')
    def _compute_fee_structure_name(self):
        unique_number = datetime.now().strftime("%Y%m%d%H%M%S%f")
        for record in self:
            if len(record.field_of_study_ids) == 1:
                field_of_study_name = record.field_of_study_ids.name
            elif record.school_id:
                field_of_study_name = record.school_id.name
            else:
                field_of_study_name = "FIL_MULTI"
            level_name = record.level_id.name
            type_frais_name = record.type_frais_id.name
            type_paiement = record.type_paiement
            year_name = record.academic_year.name
            record.fee_structure_name = f"Frais_{type_frais_name or ''}_{field_of_study_name or ''}_{level_name or ''}_{type_paiement or ''}_{year_name or ''}_{unique_number or ''}"


    def diviser_montant(self, montant, nb_tranche):        
        # Calcule la part pour chaque partie
        part = montant / nb_tranche
        # Crée une liste avec toutes les parties égales
        parties = [part] * nb_tranche
        # Retourne la liste des montants
        return parties  
    
    
    @api.onchange('type_inclusion_fee')
    # @api.depends('type_inclusion_fee')
    def change_type_inclusion_fee(self):
        if (self.type_inclusion_fee=='fee_inscrip' or 
            self.type_inclusion_fee=='fee_spec'):
            self.type_paiement='pu'
        if self.type_inclusion_fee=='fee_scol':
            self.type_paiement='pt'
        

    def validate_structure_payment(self):
        """Validate"""
        for rec in self:
            rec.state = 'validate'


    def cancel_structure_payment(self):
        """cancel"""
        for rec in self:
            rec.state = 'create'


    @api.onchange('nbre_tranche')
    @api.depends('type_paiement', 'amount_total', 'nbre_tranche')
    def _create_tranche(self):
        _logger.info("============= "+self.type_paiement)
        for rec in self:
            _logger.info(f"============= {rec}")
            if rec.type_paiement == 'pt':
                rec.fee_type_ids.unlink() 
                if rec.nbre_tranche>1:
                    parties = self.diviser_montant(rec.amount_total, rec.nbre_tranche)
                    for i, amount in enumerate(parties):
                        rec.fee_type_ids = [(0, 0, {
                            'name':f"{i+1}_tranche",
                            'fee_structure_id':rec.id,
                            'fee_amount':amount,
                        })]
                if rec.nbre_tranche<=0:
                    raise ValidationError("""Aucune Le nombre de tranche doit être supérieur à 1""")
            else:
                pass
        

    @api.model
    def create(self, vals):
        # _logger.info(vals)
        # field_of_study_ids = vals['field_of_study_ids']
        # type_frais_id = vals['type_frais_id']
        # type_paiement = vals['type_paiement']
        # academic_year = vals['academic_year']
        # level_id = vals['level_id']
        # _logger.info(field_of_study_ids)
        # students = []
        # structure_frais_id = self.env['siantou.ems.fee.structure'].search([
        #     ('academic_year', '=', academic_year),
        #     ('level_id', '=', level_id),
        #     ('type_frais_id', '=', type_frais_id),
        #     ('type_paiement', '=', type_paiement),
        #     ('field_of_study_ids','in', field_of_study_ids[0]),
        # ])
        # if structure_frais_id:
        #     raise ValidationError(f"Il y'a une structure de frais qui existe déjà pour le niveau sélectionné et contenant toutes ou certaines des filières sélectionnées")

        res = super().create(vals)

        res.update({
            "state":'create'
        })
        return res


    @api.onchange('school_id')
    def _onchange_school_id(self):
        if self.school_id:
            # Récupérer les filières associées à l'école sélectionnée
            fields_of_study = self.env['siantou.ems.core.field_of_study'].search([
                ('school_id', '=', self.school_id.id)
            ])
            # Remplir le champ des filières avec les IDs des filières trouvées
            self.field_of_study_ids = [(6, 0, fields_of_study.ids)]
        else:
            # Si aucune école n'est sélectionnée, vider le champ des filières
            self.field_of_study_ids = [(5, 0, 0)]


    def add_account_move(self):
        students = []
        account_move_created = []
        _logger.info("=============add_account_move=============")
        for rec in self:
            journal_id = rec.type_frais_id.category_id.journal_id
            for field_of_study_id in rec.field_of_study_ids:
                student_ids = field_of_study_id.student_ids.search([
                    ('level_id','=',rec.level_id.id),
                    ('field_of_study_id','=',field_of_study_id.id),
                ])
                _logger.info(f"Nombres d'étudiants :: {len(student_ids)}")
                if student_ids:
                    for student_id in student_ids:
                        _logger.info(student_id.name)
                        _logger.info(student_id.level_id.name)
                        _logger.info(student_id.field_of_study_id.name)
                        _logger.info(student_id.cycle_id.name)
                        _logger.info(rec.academic_year.name)
                        

                        students.append(student_id.id)
                        # if not account_move_ids or not len(account_move_ids)>0:
                        mone_vals = {}
                        if journal_id:
                            # account_receivable_id = journal_id.default_account_id
                            account_revenue_id = journal_id.default_account_id
                            if account_revenue_id: 
                                mone_vals['move_type'] = 'out_invoice'
                                mone_vals['partner_id'] = student_id.partner_id.id
                                mone_vals['journal_id'] = journal_id.id
                                mone_vals['invoice_date'] = fields.Date.today()
                                mone_vals['invoice_date_due'] = fields.Date.today()
                                mone_vals['annee_academique_id'] = rec.academic_year.id
                                mone_vals['level_id'] = student_id.level_id.id
                                mone_vals['filiere_id'] = student_id.field_of_study_id.id
                                mone_vals['specialite_id'] = student_id.specialty_id.id
                                mone_vals['cycle_id'] = student_id.field_of_study_id.cycle_id.id
                                mone_vals['ecole_id'] = student_id.field_of_study_id.school_id.id
                                mone_vals['type_inclusion_fee'] = rec.type_inclusion_fee

                                if rec.type_inclusion_fee=='fee_scol':
                                    account_move_ids = self.env['account.move'].search([
                                            ('partner_id','=',student_id.partner_id.id),
                                            ('type_inclusion_fee','=','fee_scol'),
                                            ('annee_academique_id','=',rec.academic_year.id),
                                            ('level_id','=',student_id.level_id.id),
                                            ('filiere_id','=',student_id.field_of_study_id.id),
                                            ('cycle_id','=',student_id.field_of_study_id.cycle_id.id),
                                        ]
                                    )
                                    _logger.info(account_move_ids)
                                    _logger.info(rec.type_inclusion_fee)
                                    _logger.info(len(account_move_ids))
                                    _logger.info(len(rec.fee_type_ids))
                                    _logger.info("==========================")
                                    if len(account_move_ids)!=len(rec.fee_type_ids):
                                        for fee_line in rec.fee_type_ids: 
                                            mone_vals['ref'] = f"Frais de {fee_line.name} de {student_id.name}"
                                            mone_vals['invoice_line_ids'] = [
                                                (0,0,{
                                                    'name': f"Frais de {fee_line.name} de {student_id.name}",
                                                    'quantity': 1.0,
                                                    'price_unit': fee_line.fee_amount,
                                                    'account_id': account_revenue_id.id,
                                                })
                                            ]
                                            account_move_id = self.env['account.move'].create(mone_vals)
                                            account_move_id.action_post()
                                            account_move_created.append(account_move_id.id)
                                    else:
                                        _logger.info(f"Tous les créances ::{rec.type_frais_id.name}:: pour {student_id.name} en {rec.academic_year.name} déjà créer")
                                    
                                elif rec.type_inclusion_fee=='fee_spec':
                                    account_move_id = self.env['account.move'].search([
                                            ('partner_id','=',student_id.partner_id.id),
                                            ('type_inclusion_fee','=','fee_spec'),
                                            ('annee_academique_id','=',rec.academic_year.id),
                                            ('level_id','=',student_id.level_id.id),
                                            ('filiere_id','=',student_id.field_of_study_id.id),
                                            ('cycle_id','=',student_id.field_of_study_id.cycle_id.id),
                                        ],
                                        limit=1
                                    )
                                    if not account_move_id:
                                        mone_vals['ref'] = f"Frais de {rec.type_frais_id.name} de {student_id.name}"
                                        mone_vals['invoice_line_ids'] = [
                                            (0,0,{
                                                'name': f"Frais de {rec.type_frais_id.name} de {student_id.name}",
                                                'quantity': 1.0,
                                                'price_unit': rec.amount_total,
                                                'account_id': account_revenue_id.id,
                                            })
                                        ]
                                        account_move_id = self.env['account.move'].create(mone_vals)
                                        account_move_id.action_post()
                                        account_move_created.append(account_move_id.id)
                                    else:
                                        _logger.info(f"Tous les créances ::{rec.type_frais_id.name}:: pour {student_id.name} en {rec.academic_year.name} déjà créer")
                                    
                                # account_move_id = self.env['account.move'].create(mone_vals)
                                # account_move_id.action_post()
                                mone_vals = {}
                                

            if account_move_created:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'success',
                        'message': f"{len(account_move_created)} créances crées pour {len(students)}",
                        'next': {'type': 'ir.actions.act_window_close'},
                    }
                }



class FeeStructureLines(models.Model):
    _name = 'siantou.ems.fee.structure.lines'


    name = fields.Char("Libellé", required=True)
    fee_structure_id = fields.Many2one(
        'siantou.ems.fee.structure', 
        string='Structure de frais', 
        ondelete='cascade', index=True, 
        required=True
    )
    fee_amount = fields.Float('Montant',  required=True)
    echeance = fields.Date("Echeance de paiement", store=True) 
    date_bu = fields.Date("Echeance de paiement") 




class FeeType(models.Model):
    _name = 'siantou.ems.fee.type'
    _inherits = {'product.product': 'product_variant_id'}

    category_id = fields.Many2one('siantou.ems.fee.category', string='Catégorie', required=True,
                                  default=lambda self: self.env['siantou.ems.fee.category'].search([], limit=1))

    @api.model
    def create(self, vals):
        category_id = self.env['siantou.ems.fee.category'].browse(
            vals.get('category_id'))
        vals.update({
            'property_account_income_id': category_id.journal_id.default_account_id,
        })
        res = super(FeeType, self).create(vals)
        return res




class FeeMoratoire(models.Model):
    _name = 'siantou.ems.fee.moratoire'
    _rec_name="student_id"

    # name = fields.Char("Nom", related='student_id.name')
    student_id = fields.Many2one('oe.school.student', string='Etudiant', required=True)
    year_id = fields.Many2one(
        'siantou.ems.core.year', 
        string='Année académique', 
        required=True,
        default=lambda self: self.env['siantou.ems.core.year'].search([('active','=',True)], limit=1),    
    )
    amount = fields.Monetary('Montant à verser', required=True, tracking=True)
    date_debut = fields.Date(string="Date de début", required=True)
    date_fin = fields.Date(string="Date de début", required=True)
    currency_id = fields.Many2one(
        'res.currency', 
        default=lambda self: self.env.company.currency_id, 
        readonly=True, 
        related_sudo=False
    )
    state = fields.Selection(
        [
            ('no_create', "Encours de création"),
            ('create', 'Crée et attente de validation'),
            ('validate', 'Validé'), 
        ],
        "Statut", 
        required=True,
        default='no_create',
    )


    def validate_moratoire(self):
        """validate moratoire"""
        for rec in self:
            rec.state = 'validate'


    def cancel_moratoire(self):
        """Cancel moratoire"""
        for rec in self:
            rec.state = 'create'
    

    def create(self, values):
        res = super(FeeMoratoire, self).create(values)
        res.update({
            'state':'create'
        })
        return res

    