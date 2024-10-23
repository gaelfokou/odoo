# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SaveXLSXWizard(models.TransientModel):
    _name = 'oe.feeslip.save.xlsx.wizard'
    _description = "Save Fee Slips"

    file_name = fields.Binary('Excel Report File')
    document_frame = fields.Char('File To Download')
