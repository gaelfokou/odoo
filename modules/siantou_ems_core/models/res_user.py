from odoo import fields, models

class ResUsers(models.Model):
    _inherit = 'res.users'

    admin_category_id = fields.Many2one(
        'ir.module.category',
        string="Admin Category",
        default=lambda self: self.env.ref('base.module_category_administration')
    )
