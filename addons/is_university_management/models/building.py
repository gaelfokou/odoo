from odoo import models, fields


class UniversityBuilding(models.Model):
    _name = 'is.university.building'
    _description = 'Bâtiments'

    name = fields.Char(
        string="Bâtiment", required=True
    )

    university_id = fields.Many2one(
        'res.company',
        required=True,
        string="Université",
        default=lambda self: self.env.company
    )

    address_id = fields.Many2one(
        'res.partner',
        required=True,
        string="Localisation",
        domain="['|', ('company_id', '=', False), ('company_id', '=', university_id)]"
    )
