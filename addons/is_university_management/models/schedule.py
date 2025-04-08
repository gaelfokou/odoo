from odoo import models, fields


class TimetableSchedule(models.Model):
    _name = 'is.university.school.timetable.schedule'
    _description = 'Horaires de l\'emploi du temps'

    timetable_id = fields.Many2one(
        'is.university.school.timetable',
        string='Emploi du temps',
        required=True
    )

    batch_id = fields.Many2one(
        'is.university.school.student.batch',
        string='Lot d\'étudiants',
        required=True
    )

    classroom_id = fields.Many2one(
        'is.university.building.classroom',
        string='Salle de classe',
        required=True
    )

    teacher_id = fields.Many2one(
        'is.university.teacher',
        string='Enseignant',
        required=True
    )

    program_id = fields.Many2one(
        'is.university.school.program',
        string='Programme',
        required=True
    )

    day_of_week = fields.Selection([
        ('monday', 'Lundi'),
        ('tuesday', 'Mardi'),
        ('wednesday', 'Mercredi'),
        ('thursday', 'Jeudi'),
        ('friday', 'Vendredi'),
        ('saturday', 'Samedi'),
    ], string='Jour de la semaine', required=True)

    start_time = fields.Float(
        string='Heure de début',
        required=True
    )

    end_time = fields.Float(
        string='Heure de fin',
        required=True
    )