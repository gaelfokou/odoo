# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging
from datetime import datetime

_logger = logging.getLogger("Logger ==========")


class LissteFacture(models.AbstractModel):
    _name = 'report.siantou_ems_fee.report_fees_classe'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["siantou.ems.fee.classe"].search([('id', 'in', docids)])
        students = []

        for doc in docs:
            for student in doc.classe_id.student_ids:
                total = 0
                fees = self.env['account.move'].search([('partner_id', '=', student.partner_id.id),('academic_year_id', '=', doc.academic_year.id)])
                total = sum([x.amount_total for x in fees])
                students.append({
                    'matricule': student.matricule,
                    'name': student.name,
                    'amount': total,
                    'reste': total,
                })

        
        docargs = {
            'doc_ids': docids,
            'doc_model': "siantou.ems.fee.classe",
            'docs': docs,
            'data': data,
            'students': students
        }

        return docargs