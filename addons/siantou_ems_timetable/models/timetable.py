from email.policy import default

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Timetable(models.Model):
    _name = 'siantou.ems.timetable.timetable'
    _description = 'Emplois du temps'

    # Semestre liée à la programmation de cours
    semester_id = fields.Many2one(
        'siantou.ems.core.year.semester',
        'Semestre',
        required=True,
        ondelete='restrict'
    )

    # Filière liée à la programmation de cours
    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        'Filière',
        required=True,
        ondelete='restrict'
    )

    # Niveau lié à la programmation de cours
    level_id = fields.Many2one(
        'siantou.ems.core.level',
        'Niveaux',
        required=True,
        ondelete='restrict'
    )

    # Cours programmé
    subject_id = fields.Many2one(
        'siantou.ems.core.subject',
        'Cours',
        required=True,
        ondelete='restrict'
    )

    # Salle liée à la programmation de cours
    classroom_id = fields.Many2one(
        'siantou.ems.core.building.classroom',
        'Salle de classe',
        required=True,
        ondelete='restrict'
    )

    # Professeur lié à la programmation de cours
    employee_id = fields.Many2one(
        'hr.employee',
        'Professeur',
        required=True,
        ondelete='restrict'
    )

    # Jour où le cours est programmé
    day_of_week = fields.Selection([
        ('0', 'Lundi'),
        ('1', 'Mardi'),
        ('2', 'Mercredi'),
        ('3', 'Jeudi'),
        ('4', 'Vendredi'),
        ('5', 'Samedi'),
    ], 'Jour de la semaine',
        required=True
    )

    # Heure de début du cours
    start_time = fields.Float(
        'Heure de début',
        required=True,
        default=0,
        ondelete='restrict',
        widget='time'
    )

    # Heure de fin du cours
    end_time = fields.Float(
        'Heure de fin',
        required=True,
        default=0,
        ondelete='restrict',
        widget='time'
    )

    # Contrainte logique pour se rassurer qu'on a pas deux enregistrements identiques
    @api.constrains('field_of_study_id', 'level_id', 'subject_id', 'classroom_id', 'employee_id', 'day_of_week', 'start_time', 'end_time')
    def _check_duplicate(self):
        for record in self:
            if self.search([
                ('field_of_study_id', '=', record.field_of_study_id.id),
                ('level_id', '=', record.level_id.id),
                ('subject_id', '=', record.subject_id.id),
                ('classroom_id', '=', record.classroom_id.id),
                ('employee_id', '=', record.employee_id.id),
                ('day_of_week', '=', record.day_of_week),
                ('start_time', '=', record.end_time),
                ('end_time', '=', record.start_time),
            ]):
                raise ValidationError("Cet enregistrement existe déjà")

    #Contrainte logique pour se rassurer que deux cours ne sont pas programmés dans la même salle au même moment
    @api.constrains('classroom_id', 'day_of_week', 'start_time', 'end_time')
    def _check_classroom_is_free(self):
        for record in self:
            if self.search([
                ('id', '!=', record.id),
                ('classroom_id', '=', record.classroom_id.id),
                ('day_of_week', '=', record.day_of_week),
                ('start_time', '<=', record.end_time),
                ('end_time', '>=', record.start_time),
            ]):
                raise ValidationError("Deux salles de classe ne doivent pas être programmées sur des horaires qui se chevauchent le même jour")

    # Contrainte logique pour s'assurer que l'heure de fin est supérieure à l'heure de début
    @api.constrains('start_time', 'end_time')
    def _check_time(self):
        for record in self:
            if record.end_time <= record.start_time:
                raise ValidationError("L'heure de fin du cours doit être supérieure à l'heure de début du cours")

    # Contrainte logique pour s'assurer que les heures de début et de fin sont définies
    @api.constrains('start_time', 'end_time')
    def _check_time_is_set(self):
        for record in self:
            if record.start_time <= 0 or record.end_time <= 0:
                raise ValidationError("Vous devez définir des heures de début et de fin corrects")

    def action_timetable_automatic(self):
        action = self.env.ref('siantou_ems_timetable.action_generatetimetable_wizard').read()[0]
        action.update({
            'name': 'Planification automatique',
            'res_model': 'siantou.ems.timetable.timetable_wizard',
            'type': 'ir.actions.act_window',
        })
        return action

    def action_timetable_print(self):
        action = self.env.ref('siantou_ems_timetable.action_print_timetable_wizard').read()[0]
        action.update({
            'name': 'Impression de l\'emploi du temps',
            'res_model': 'siantou.ems.timetable.timetable_print_wizard',
            'type': 'ir.actions.act_window',
        })
        return action