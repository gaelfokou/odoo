# -*- coding: utf-8 -*-


from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging


_logger = logging.getLogger(__name__)

class FeeStructure(models.Model):
    _name = 'siantou.ems.fee.structure'
    _rec_name = 'fee_structure_name'


    _sql_constraints = [
        ('unique_fee_structure_name', 'unique(fee_structure_name)', 'Ce nom existe déjà'),
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
    # category_id = fields.Many2one(
    #     'siantou.ems.fee.type', string='Catégorie', required=True,
    #     default=lambda self: self.env['siantou.ems.fee.category'].search(
    #         [], limit=1),
    #     domain=[('fee_structure', '=', True)])
    type_frais_id = fields.Many2one(
        'siantou.ems.fee.type', string='Type de frais', required=True)
    field_of_study_id = fields.Many2one('siantou.ems.core.field_of_study', required=True,string='Filière')
    level_id = fields.Many2one('siantou.ems.core.level', required=True,string='Niveau')
    
    # is_assurance = fields.Boolean('Est un frais d\'assurance ?', default=False)
    # is_inscription = fields.Boolean("Est un frais d'inscription ?", default=False)
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
        compute='_create_tranche',
        store=True,
    )
    nbre_tranche = fields.Integer("Nombre de tranches", required=True, default=1,)
    sequence = fields.Integer('Priorité', default=1, required=True, store=True)
    # fee_special = fields.Boolean('Inclure dans les frais spéciaux', default=False)
    # is_scolarite = fields.Boolean("Est un frais de scolarité ?", default=False) 
    active = fields.Boolean(default=True)


    @api.depends('field_of_study_id', 'level_id', 'type_frais_id', 'type_paiement')
    def _compute_fee_structure_name(self):
        for record in self:
            # Calculer 'fee_structure_name' en fonction de 'field_of_study_id' et 'level_id'
            field_of_study_name = record.field_of_study_id.name
            level_name = record.level_id.name
            type_frais_name = record.type_frais_id.name
            type_paiement = record.type_paiement
            record.fee_structure_name = f"Frais_{type_frais_name or ''}_{field_of_study_name or ''}_{level_name or ''}_{type_paiement or ''}"



    def diviser_montant(self, montant, nb_tranche):        
        # Calcule la part pour chaque partie
        part = montant / nb_tranche
        # Crée une liste avec toutes les parties égales
        parties = [part] * nb_tranche
        # Retourne la liste des montants
        return parties  


    # @api.onchange('nbre_tranche')
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
                        # self.env['siantou.ems.fee.structure.lines'].create({
                        #     'line_name':f"{i+1} tranche",
                        #     # 'fee_structure_id':self.id,
                        #     'fee_amount':amount,
                        # })
                if rec.nbre_tranche<=0:
                    raise ValidationError("""Aucune Le nombre de tranche doit être supérieur à 1""")
            else:
                pass
        
        

    # @api.depends("field_of_study_id", "level_id")
    # def _get_name(self):
    #     self.fee_structure_name = "Structure de frais {}"

    @api.model
    def create(self, vals):
        res = super().create(vals)
        # self._create_tranche(res)
        return res



class FeeStructureLines(models.Model):
    _name = 'siantou.ems.fee.structure.lines'


    name = fields.Char("Libellé", required=True)
    fee_structure_id = fields.Many2one(
        'siantou.ems.fee.structure', string='Structure de frais', ondelete='cascade', index=True, required=True)
    fee_amount = fields.Float('Montant',  required=True)
    echeance = fields.Date("Echeance de paiement")




class FeeType(models.Model):
    _name = 'siantou.ems.fee.type'
    _inherits = {'product.product': 'product_variant_id'}

    # _sql_constraints = [
    #     ('unique_line_name', 'unique(line_name)', 'Ce nom existe déjà'),
    # ]

    # payment_type = fields.Selection([
    #                                 ('onetime', 'Une fois'),
    #                                 ('permonth', 'Par mois'),
    #                                 ('peryear', 'Par an'),
    #                                 ('sixmonth', 'Pour 6 mois'),
    #                                 ('threemonth', 'Pour 3 mois')
    #                                 ], string='Type de paiement', default='permonth',
    #                                 help='Payment type describe how much a payment effective.'
    #                                 ' Like, bus fee per month is 30 dollar, sports fee per year is 40 dollar, etc')
    # interval = fields.Char('Intervale de paiement', help='Interval describe the payment mode of the fee.'
    #                                                 'For example, Monthly means the fee must be paid in each month.'
    #                                                 'Yearly means the payment paid only one time uin year.')

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
