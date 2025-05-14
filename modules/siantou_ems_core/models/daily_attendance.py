# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class DailyAttendance(models.Model):
    _inherit = 'daily.attendance'

    def action_open_filter(self):
        view_id = self.env.ref('siantou_ems_core.daily_attendance_filter_wizard').id
        return {
            'name': 'Filtre des présences',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'daily.attendance.filter.wizard',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
        }

    def action_reset_filter(self):
        self.env['ir.config_parameter'].sudo().set_param(f'filter.{self.env.user.id}', '')
        action = self.env.ref('siantou_ems_core.action_show_daily_attendance').read()[0]
        action.update({
            'target': 'main',
        })
        return action

    def action_print_pdf(self):
        active_ids = self.env.context.get('active_ids', [])
        attendances = self.env['daily.attendance'].browse(active_ids)
        if len(active_ids) == 0:
            raise UserError('Aucune donnée sélectionnée')
        report_data = self.env['daily.attendance.print.wizard'].create({})
        domain = [('id', 'in', active_ids)]
        data = report_data.print_daily_attendance_report_data(domain)

        # Appeler le rapport PDF
        if not data['docdata']['attendance_data']:
            raise UserError('Aucune donnée trouvée')
        report_action = self.env.ref('siantou_ems_core.action_report_daily_attendance')
        return report_action.report_action(self, data=data)
