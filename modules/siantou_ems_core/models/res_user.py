from odoo import fields, models

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