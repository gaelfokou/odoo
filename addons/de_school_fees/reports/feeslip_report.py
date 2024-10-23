# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from psycopg2 import sql

from odoo import api, fields, models, tools


class FeeslipReport(models.Model):
    _name = "oe.feeslip.report"
    _description = "Feeslip Analysis Report"
    _auto = False
    _rec_name = 'date_from'
    _order = 'date_from desc'

    @api.model
    def _get_done_states(self):
        return ['sale', 'done']

    nbr = fields.Integer('# of Lines', readonly=True)
    name = fields.Char(string="Name") 
    student_id = fields.Many2one('res.partner',string='Student', readonly=True)
    fee_struct_id = fields.Many2one('oe.fee.struct', string='Fee Struct', readonly=True)
    course_id = fields.Many2one('oe.school.course',string='Couse', readonly=True)
    batch_id = fields.Many2one('oe.school.course.batch', string='Batch', readonly=True)
    date_from = fields.Date(string='Date From', readonly=True)
    date_to = fields.Date(string='Date To', readonly=True)
    company_id = fields.Many2one('res.company',string='Company', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('paid', 'Paid'),
        ('cancel', 'Rejected')],
        string='Status', readonly=True)
    amount_total = fields.Float(string='Total Fee', readonly=True)
    fee_name = fields.Char(string='Fee Name', readonly=True)
    fee_amount = fields.Float(string='Fee Amount', readonly=True)


    @property
    def _table_query(self):
        ''' Report needs to be dynamic to take into account multi-company selected + multi-currency rates '''
        return '%s %s %s %s' % (self._select(), self._from(), self._where(), self._group_by())

    def _select(self):
        select_str = """
                SELECT
                    min(slip.id) as id, 
                    slip.name, 
                    slip.student_id,
                    slip.fee_struct_id,
                    std.course_id,
                    std.batch_id,
                    slip.date_from, slip.date_to,
                    slip.company_id,
                    slip.state,
                    sum(slip.amount_total) as amount_total, 
                    line.name as fee_name,
                    sum(line.total) as fee_amount
        """
        return select_str
        
    def _from(self):
        from_str = """
            FROM
            oe_feeslip slip
            join oe_feeslip_line line on line.feeslip_id = slip.id
            join res_partner std on slip.student_id = std.id
        """
        return from_str
    
    def _where(self):
        return """
            WHERE
                slip.name is not null
        """

    def _group_by(self):
        group_by_str = """
            GROUP BY
                slip.name, 
                slip.student_id,
                slip.fee_struct_id,
                std.course_id,
                std.batch_id,
                slip.date_from, slip.date_to,
                slip.company_id,
                slip.state,
                slip.amount_total, 
                line.name,
                line.total
        """
        return group_by_str
    