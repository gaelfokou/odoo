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
        _logger.info(f'----------- tototototototo is_user {is_user} -----------')
        if not is_user:
            menu_item_id = self.env.ref('siantou_ems_core.menu_siantou_ems_core_portal').id
            menus.discard(menu_item_id)
        return menus

    def switch_to_portal(self, user):
        partner_id = user.partner_id
        company_id = None
        if user.company_id.id:
            company_id = user.company_id
        elif partner_id.company_id.id:
            company_id = partner_id.company_id
        employee_id = self.env['hr.employee'].search([
            ('work_email', '=', user.login),
        ], limit=1)
        if employee_id:
            password = employee_id.identifier
            employee_id.write({
                'user_id': user.id,
                'work_email': user.login,
            })
            if employee_id.is_teacher:
                group_id = self.env.ref('base.group_portal')
                user.write({
                    'password' : password,
                    'groups_id': [(6, 0, [group_id.id])],
                    'employee_id': employee_id.id,
                })
            else:
                group_id = self.env.ref('base.group_user')
                user.write({
                    'password' : password,
                    'groups_id': [(6, 0, [group_id.id])],
                    'employee_id': employee_id.id,
                })
            partner_id.write({
                'name': employee_id.name,
                'email': employee_id.work_email,
                'phone': employee_id.work_phone,
                'is_company': False,
                'company_id': company_id.id,
                'user_id': user.id,
                'employee': True,
            })
        else:
            student_id = self.env['oe.school.student'].search([
                ('email', '=', user.login),
            ], limit=1)
            if student_id:
                password = student_id.matricule
                student_id.write({
                    'user_id': user.id,
                    'email': user.login,
                })
                group_id = self.env.ref('base.group_portal')
                user.write({
                    'password' : password,
                    'groups_id': [(6, 0, [group_id.id])],
                    'student_id': student_id.id,
                })
                partner_id.write({
                    'name': student_id.name,
                    'email': student_id.email,
                    'phone': student_id.private_phone,
                    'is_company': False,
                    'company_id': company_id.id,
                    'user_id': user.id,
                    'employee': False,
                })

    @api.model
    def create(self, vals):
        # Création de l'utilisateur
        user = super(ResUsers, self.with_context(no_reset_password=True)).create(vals)

        self.create_user_employee_or_student(user)

        return user
