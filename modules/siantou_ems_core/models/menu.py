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
        is_user = None
        if self.env.user.employee_id.id:
            user = self.env.user.employee_id
            if self.env.user.employee_id.is_teacher and self.env.user.employee_id.is_portal:
                is_user = 'is_portal'
        if not is_user:
            menu_item_id = self.env.ref('siantou_ems_core.menu_siantou_ems_core_portal').id
            menus.discard(menu_item_id)
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

        return {
            'type': 'ir.actions.act_url',
            'url': 'http://127.0.0.1:8069/my',
            'target': 'self',
        }
