from odoo import models, fields


class BuildingClassroom(models.Model):
    _name = 'is.university.building.classroom'
    _description = 'Salles de classe'

    name = fields.Char(
        string="Nom",
        required=True
    )

    building_id = fields.Many2one(
        'is.university.building',
        'Bâtiment'
    )

    capacity = fields.Integer(
        string="Capacité"
    )
