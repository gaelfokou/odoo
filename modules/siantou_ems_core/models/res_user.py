
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, tools, _

class ResUsers(models.Model):
    _inherit = 'res.users'

    def create_user_employee_or_student(self, user):
        employee_id = self.env['hr.employee'].search([
            ('work_email', '=', user.login),
        ], limit=1)
        if employee_id:
            password = employee_id.identifier
            if employee_id.is_teacher:
                group_id = self.env.ref('base.group_portal')
                user.write({
                    'password' : password,
                    'groups_id': [(6, 0, [group_id.id])],
                })
            else:
                group_id = self.env.ref('base.group_user')
                user.write({
                    'password' : password,
                    'groups_id': [(6, 0, [group_id.id])],
                })
            employee_id.write({
                'user_id': user.id,
            })
        else:
            student_id = self.env['oe.school.student'].search([
                ('email', '=', user.login),
            ], limit=1)
            if student_id:
                password = student_id.matricule
                group_id = self.env.ref('base.group_portal')
                user.write({
                    'password' : password,
                    'groups_id': [(6, 0, [group_id.id])],
                })
                student_id.write({
                    'user_id': user.id,
                })

    @api.model
    def create(self, vals):
        # Création de l'utilisateur
        user = super(ResUsers, self.with_context(no_reset_password=True)).create(vals)

        self.create_user_employee_or_student(user)

        return user
