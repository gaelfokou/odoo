# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _
import logging

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    employee_id = fields.Many2one(
        'hr.employee',
        'Enseignant',
        ondelete='cascade'
    )

    student_id = fields.Many2one(
        'oe.school.student',
        string='Étudiant',
        ondelete='cascade',
    )

    read_group_ids = fields.Many2many(
        'siantou.ems.timetable.group',
        'read_user_group_rel',
        'user_id',
        'group_id',
        string='Versions d\'emploi du temps en lecture',
    )

    write_group_ids = fields.Many2many(
        'siantou.ems.timetable.group',
        'write_user_group_rel',
        'user_id',
        'group_id',
        string='Versions d\'emploi du temps en écriture',
    )

    request_ids = fields.Many2many(
        'siantou.ems.core.request.track',
        'read_user_request_rel',
        'user_id',
        'request_id',
        string='Requêtes',
    )

    def create_user_employee_or_student(self, user):
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
                    'password': password,
                    'groups_id': [(6, 0, [group_id.id])],
                    'employee_id': employee_id.id,
                })
            else:
                group_id = self.env.ref('base.group_user')
                user.write({
                    'password': password,
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
                    'password': password,
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
