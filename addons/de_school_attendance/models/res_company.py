# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    student_attendance_mode = fields.Selection([
        ('day', 'By Day'),
        ('period', 'By Subject / Period'),
    ], string='Student Attendance Mode', default='day')
    student_attendance_with_time = fields.Boolean('Mark Attendance with Time')
    
    student_attendance_kiosk_mode = fields.Selection([
        ('barcode', 'Barcode / RFID'),
        ('barcode_manual', 'Barcode / RFID and Manual Selection'),
        ('manual', 'Manual Selection'),
    ], string='Student Attendance KIOSK Mode', default='barcode_manual')
    student_attendance_barcode_source = fields.Selection([
        ('scanner', 'Scanner'),
        ('front', 'Front Camera'),
        ('back', 'Back Camera'),
    ], string='Student Barcode Source', default='front')
    student_attendance_kiosk_delay = fields.Integer(default=10)

    def _enable_attendance_menu(self):
        if self.student_attendance_mode == 'day':
            self.email = 'day@day123.com'
        else:
            self.email = 'period@period123.com'
        
    @api.model_create_multi
    def create1(self, vals_list):
        companies = super(ResCompany, self).create(vals_list)
        for company in companies:
            company.sudo()._enable_attendance_menu()

    def write111(self, values):
        res = super(ResCompany, self).write(values)
        for company in self:
            company.sudo()._enable_attendance_menu()
        return res


