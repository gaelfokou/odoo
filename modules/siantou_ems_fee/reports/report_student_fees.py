# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging
from datetime import datetime
# from odoo.addons.siantou_ems_fee.models.utils import get_amount_en_lettre

_logger = logging.getLogger("Logger ==========")


class StudentFacture(models.AbstractModel):
    _name = 'report.siantou_ems_fee.report_student_fees'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["oe.school.student"].search([('id', 'in', docids)])
        lines = []
        total = 0
        for doc in docs:
            fees = self.env['account.move'].search([('partner_id', '=', doc.partner_id.id),('academic_year_id', '=', doc.class_id.academic_year_id.id),('journal_id.is_fee','=', True)])
            total = sum([x.amount_residual for x in fees])
            for fee in fees:
                lines.append({
                    'frais': fee.journal_id.name.upper(),
                    'amount': fee.amount_total,
                    'reste': fee.amount_residual,
                })

        
        docargs = {
            'doc_ids': docids,
            'doc_model': "oe.school.student",
            'docs': docs,
            'data': data,
            'lines': lines,
            'total': total,
            # 'lettre' : get_amount_en_lettre(total),
            'date': fields.date.today()
        }

        return docargs