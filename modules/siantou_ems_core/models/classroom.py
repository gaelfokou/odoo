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

    school_ids = fields.Many2many('siantou.ems.core.school', 'school_building_rel', 'building_id', 'school_id', string='Écoles')

    # Variable booléenne pour préciser si le bâtiment est opérationnel
    is_active = fields.Boolean(
        default=True
    )

class Classroom(models.Model):
    _name = 'siantou.ems.core.building.classroom'
    _description = 'Salles de classe'

    # Code de la salle de classe
    code = fields.Char(
        string='Code',
        required=True,
        help="Code unique pour identifier la salle de classe."
    )

    # Nom de la salle de classe
    name = fields.Char(
        string='Nom de la salle',
        required=True,
        index=True,
        translate=True,
        help="Nom descriptif de la salle de classe."
    )

    # Bâtiment auquel appartient la salle de classe
    building_id = fields.Many2one(
        'siantou.ems.core.building',
        string='Bâtiment',
        required=True,
        index=True,
        help="Bâtiment auquel cette salle de classe est associée."
    )

    # Capacité de la salle de classe
    capacity = fields.Integer(
        string='Capacité',
        required=True,
        default=60,
        help="Nombre maximal d'étudiants pouvant être accueillis dans cette salle."
    )

    # Relation avec les emplois du temps
    timetable_ids = fields.One2many(
        'siantou.ems.timetable.timetable',  # Nom du modèle cible
        'classroom_id',                     # Champ de relation dans le modèle Timetable
        string='Emplois du temps',
        help="Liste des emplois du temps associés à cette salle de classe."
    )

    is_cours_active = fields.Boolean(string="Actif pour les cours", default=False)

    is_examen_active = fields.Boolean(string="Actif pour les examens", default=False)

    # Contrainte SQL pour garantir que le code de la salle de classe est unique
    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code de la salle de classe doit être unique.'),
    ]

    # Contrainte logique pour vérifier que la capacité est strictement positive
    @api.constrains('capacity')
    def _check_capacity(self):
        for record in self:
            if record.capacity <= 0:
                raise ValidationError('La capacité doit être supérieure à 0')