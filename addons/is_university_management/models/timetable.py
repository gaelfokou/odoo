from odoo import models, fields, api, exceptions
from datetime import timedelta


class SchoolTimetable(models.Model):
    _name = 'is.university.school.timetable'
    _description = 'Emploi du temps universitaire'

    program_id = fields.Many2one(
        'is.university.school.program',
        string='Programme'
    )

    semester_id = fields.Many2one(
        'is.university.semester',
        string='Semestre'
    )

    batch_id = fields.Many2one(
        'is.university.school.student.batch',
        string='Lot d\'étudiants'
    )

    subject_id = fields.Many2one(
        'is.university.subject',
        string='Cours'
    )

    classroom_id = fields.Many2one(
        'is.university.building.classroom',
        string='Salle de classe'
    )

    teacher_id = fields.Many2one(
        'is.university.teacher',
        string="Enseignant"
    )

    start_time = fields.Float(
        string='Heure de début'
    )

    end_time = fields.Float(
        string='Heure de fin'
    )

    def action_open_generate_wizard(self):
        return {
            'name': 'Génération de l\'emploi du temps',
            'type': 'ir.actions.act_window',
            'res_model': 'is.university.school.timetable.wizard',
            'view_mode': 'form',
            'target': 'new',
        }