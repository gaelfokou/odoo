from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.tools import unique

class Campus(models.Model):
    _name = 'siantou.ems.core.campus'
    _description = 'Campus'

    # Code
    code = fields.Char(
        'Code',
        required=True
    )

    # Nom
    name = fields.Char(
        string="Nom du campus",
        required=True
    )

    # Université à laquelle appartient ce bâtiment
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company
    )
    

class Building(models.Model):
    _name = 'siantou.ems.core.building'
    _description = 'Bâtiments'

    # Code du bâtiment
    code = fields.Char(
        'Code',
        required=True
    )

    # Nom du bâtiment
    name = fields.Char(
        string="Nom du bâtiment",
        required=True
    )

    address_id = fields.Many2one(
        'siantou.ems.core.campus',
        required=True,
        string="Campus",
    )

    # Variable booléenne pour préciser si le bâtiment est opérationnel
    active = fields.Boolean(
        default=True
    )


class Classroom(models.Model):
    _name = 'siantou.ems.core.building.classroom'
    _description = 'Salles de classe'

    # Code de la salle de classe
    code = fields.Char(
        'Code',
        required=True
    )

    # Nom de la salle de classe
    name = fields.Char(
        'Nom de la salle',
        required=True,
        index=True,
        translate=True
    )

    # Bâtiment auquel appartient la salle de classe
    building_id = fields.Many2one(
        'siantou.ems.core.building',
        'Bâtiment',
        required=True,
        index=True,
    )

    # Capacité de la salle de classe
    capacity = fields.Integer(
        'Capacité',
        required=True,
        default=60
    )

    #Contrainte SQL pour s'assurer que la salle de classe est unique
    _sql_constraints = [
        ('unique_code', 'unique(code)', 'La salle de classe doit être unique')
    ]

    # Contrainte logique pour s'assurer que la date de fin est supérieure à la date de début
    @api.constrains('capacity')
    def _check_capacity(self):
        for record in self:
            if record.capacity <= 0:
                raise ValidationError("La capacité doit être strictement supérieur à 0.")