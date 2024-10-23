# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SaveXLSXWizard(models.TransientModel):
    _name = 'oe.attendance.save.xlsx'
    _description = "Save Excel Report File"

    file_name = fields.Binary('Excel Report File')
    document_frame = fields.Char('File To Download')
