from odoo import models, fields


class TeacherAvailability(models.Model):
    _name = 'is.university.teacher.availability'
    _description = 'Disponibilités de l\'enseignant'

    teacher_id = fields.Many2one(
        'is.university.teacher',
        string="Enseignant",
        required=True
    )

    day_of_week = fields.Selection([
        ('monday', 'Lundi'),
        ('tuesday', 'Mardi'),
        ('wednesday', 'Mercredi'),
        ('thursday', 'Jeudi'),
        ('friday', 'Vendredi'),
        ('saturday', 'Samedi'),
    ],
        string="Jour de la semaine",
        required=True
    )

    start_time = fields.Float(
        string="Heure de début",
        required=True,
        widget="time"
    )

    end_time = fields.Float(
        string="Heure de fin",
        required=True,
        widget="time"
    )
