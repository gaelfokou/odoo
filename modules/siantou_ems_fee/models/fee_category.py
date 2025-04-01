# -*- coding: utf-8 -*-

from odoo import models, fields, api

class FeeCategory(models.Model):
    _name = 'siantou.ems.fee.category'

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Ce nom existe déjà'),
    ]

    name = fields.Char('Libellé', required=True, help='Create a fee category suitable for your institution.'
                                                   ' Like Institutuinal, Hostel, Transportation, Arts and Sports, etc')
    journal_id = fields.Many2one('account.journal', string='Journal comptable', required=True,
                                 domaine=[('is_fee', '=', True)],
                                #  default=lambda self: self.env['account.journal'].search(
                                #      [('code', '=', 'IFEE')], limit=1) if self.env['account.journal'].search(
                                #      [('code', '=', 'IFEE')], limit=1) else False,
                                 help='Setting up of unique journal for each category help to distinguish '
                                      'account entries of each category ')
    # fee_structure = fields.Boolean('Voir dans une structure?', required=True, default=False,
    #                                help='If any fee structure want to be included in this category you must click here.'
    #                                     'For an example Institution category have different kind of fee structures '
    #                                     'for different syllabuses')

#     analytic_id = fields.Many2one('account.analytic.account', string='Compte Analytique')