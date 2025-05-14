# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, tools, _
from datetime import date
from odoo.exceptions import UserError, ValidationError
_logger = logging.getLogger(__name__)

class EducationFiliere(models.Model):
    _inherit = 'siantou.ems.core.field_of_study'

    # frais = fields.Many2many(
    #     'siantou.ems.fee.structure',
    #     string='Frais ',
    #     compute='_compute_struct',
    #     store=True
    # )

    # @api.depends('cycle_id')
    # def _compute_struct(self):
    #     for rec in self:
    #         annee = self.env['siantou.ems.core.year'].search(
    #             [('active', '=', True)])
    #         fee_categorys = self.env['siantou.ems.fee.category'].search([])
    #         cats = [e.id for e in fee_categorys]
    #         strs = []
            # if rec.online != 'h':
            #     structure_ids = self.env['siantou.ems.fee.structure'].search(
            #         [('academic_year', '=', annee.id), ('fee_special', '=', False),
            #         ('category_id', 'in', cats),('cycle_id', '=', rec.cycle_id.id),
            #         ('online', 'in', [rec.online,'op'])])
            #     strs = [e.id for e in structure_ids]
            # else:
            # structure_ids = self.env['siantou.ems.fee.structure'].search([
            #     ('academic_year', '=', annee.id),
            #     ('fee_special', '=', False),
            #     ('category_id', 'in', cats),
            #     ('field_of_study_id', '=', rec.field_of_study_id.id)
            # ])
            # strs = [e.id for e in structure_ids]

            # rec.frais = [(6, 0,strs)]

# class EducationStudent(models.Model):
#     _inherit = 'oe.school.student'

#     currency_id = fields.Many2one(
#         'res.currency',
#         string='Devise',
#         default=lambda self: self.env.company.currency_id,
#     )
#     amount_to_paid = fields.Monetary(
#         compute='_compute_amount_to_paid',
#         string='Montant à payé',
#         currency_field="currency_id",
#         store=True
#     )
#     amount_paid = fields.Monetary(
#         compute='_compute_amount_paid',
#         string='Montant payé',
#         currency_field="currency_id",
#         store=True
#     )
#     percentage = fields.Float(compute='_compute_percentage',store=True, string='Poucentage de scolarite')
#     etat_scol = fields.Selection(
#         [('nok', 'Refusé'), ('ok', 'Accepté')],
#         'Statut de la Scolarité', compute='maj_statut',default='nok', store=True)

