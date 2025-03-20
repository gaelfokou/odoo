
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    admin_category_id = fields.Many2one(
        'ir.module.category',
        string="Admin Category",
        default=lambda self: self.env.ref('base.module_category_administration')
    )

    applicant_ids = fields.Many2many('hr.applicant', string="Candidatures")

    @api.model
    def get_groups_for_poste(self):
        """
        Filtre les groupes associés à la candidature "POSTES".
        """
        # Remplace 'POSTES' par la valeur réelle qui identifie cette candidature
        postes_groups = self.env['res.groups'].search([
            ('category_id.name', '=', 'POSTES')  # Catégorie ou critère à ajuster
        ])
        return postes_groups
        
    def _get_groups_domain(self):
        """
        Retourne le domaine à appliquer pour les groupes visibles.
        """
        groups = self.get_groups_for_poste()
        return [('id', 'in', groups.ids)]

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
        user = super().create(vals)

        self.create_user_employee_or_student(user)

        return user
