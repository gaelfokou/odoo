# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging
from datetime import datetime
# from odoo.addons.siantou_ems_fee.models.utils import get_amount_en_lettre

_logger = logging.getLogger("Logger ==========")


class RecuPaiement(models.AbstractModel):
    _name = 'report.account_cash_bank_management.report_recu_payment'


    @api.model
    def _get_report_values(self, docids, data=None):
        _logger.info(docids)
        
        # student_id = self.env["oe.school.student"].search([('id', '=', student_id)], limit=1)

        # lines = []
        # total = 0
        # fees = self.env['account.move'].search([
        #         ('partner_id', '=', student_id.student_enroll_id.partner_id.id),
        #         # ('academic_year_id', '=', student_id.academic_year_id.id),
        #         ('journal_id.is_fee','=', True)
        #     ]
        # )
        # _logger.info(fees)
        # total = sum([x.amount_residual for x in fees])
        # for fee in fees:
        #     lines.append({
        #         'frais': fee.journal_id.name.upper(),
        #         'amount': fee.amount_total,
        #         'reste': fee.amount_residual,
        #     })

        
        docargs = {
            'doc_model': "account.bank.statement.line",
            'data': data,
            # 'lines': lines,
            # 'total': total,
            # 'lettre' : get_amount_en_lettre(total),
            'date': fields.date.today()
        }

        return docargs