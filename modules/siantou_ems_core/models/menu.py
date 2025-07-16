# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _
import logging

_logger = logging.getLogger(__name__)

class Menu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    @tools.ormcache('frozenset(self.env.user.groups_id.ids)', 'debug')
    def _visible_menu_ids(self, debug=False):
        menus = super(Menu, self)._visible_menu_ids(debug)
        if not self.env['ir.config_parameter'].sudo().get_param(f'siantou.url_base'):
            self.env['ir.config_parameter'].sudo().set_param(f'siantou.url_base', 'http://127.0.0.1:8069')
        if not self.env['ir.config_parameter'].sudo().get_param(f'siantou.url_portal'):
            self.env['ir.config_parameter'].sudo().set_param(f'siantou.url_portal', '/my/home')
        if not self.env['ir.config_parameter'].sudo().get_param(f'siantou.url_user'):
            self.env['ir.config_parameter'].sudo().set_param(f'siantou.url_user', '/web')
        is_user = None
        if self.env.user.employee_id.id:
            user = self.env.user.employee_id
            if self.env.user.employee_id.is_teacher and self.env.user.employee_id.is_portal:
                is_user = 'is_portal'
        if not is_user:
            menu_accessibility_id = self.env.ref('siantou_ems_core.menu_siantou_ems_core_accessibility').id
            menus.discard(menu_accessibility_id)
        return menus

    def switch_to_portal(self):
        if self.env.user.employee_id.id:
            user = self.env.user
            if self.env.user.employee_id.is_teacher and self.env.user.employee_id.is_portal:
                is_user = 'is_portal'
        if is_user:
            group_user = self.env.ref('base.group_user')
            group_public = self.env.ref('base.group_public')
            group_portal = self.env.ref('base.group_portal')
            group_user.sudo().write({'users': [(3, user.id)]})
            group_portal.sudo().write({'users': [(4, user.id)]})

        url_base = self.env['ir.config_parameter'].sudo().get_param(f'siantou.url_base', 'http://127.0.0.1:8069')
        url_portal = self.env['ir.config_parameter'].sudo().get_param(f'siantou.url_portal', '/my/home')
        url_user = self.env['ir.config_parameter'].sudo().get_param(f'siantou.url_user', '/web')

        return {
            'type': 'ir.actions.act_url',
            'url': '{}{}'.format(url_base, url_portal),
            'target': 'self',
        }
