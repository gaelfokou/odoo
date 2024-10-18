from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import pprint

# Créer une instance de logger
_logger = logging.getLogger(__name__)

class SchoolTeacherScheduler(models.Model):
    _name = 'school.teacher.scheduler'
    _description = 'Teacher Scheduler for Courses'

    @api.model
    def find_best_teacher(self, date, hour_from, hour_to, subject):
        """
        Trouve l'enseignant disponible avec la priorité la plus élevée pour un créneau horaire donné et une matière,
        en vérifiant que l'enseignant n'est pas déjà assigné à un autre cours à la même période.

        :param date: Date du cours
        :param hour_from: Heure de début (float)
        :param hour_to: Heure de fin (float)
        :param subject: Objet de la matière (oe.school.subject)
        :return: L'enseignant avec la priorité la plus élevée ou lève une erreur si aucun enseignant n'est disponible.
        """
        _logger.info(f'----------- tototototototo subject_id {subject.id} -----------')
        _logger.info(f'----------- tototototototo date {date} -----------')
        _logger.info(f'----------- tototototototo hour_from {hour_from} -----------')
        _logger.info(f'----------- tototototototo hour_to {hour_to} -----------')
        # Mapping des numéros de jours (0-6) à leurs noms en anglais

        day_of_week_map = {
            0: 'Lundi',
            1: 'Mardi',
            2: 'Mercredi',
            3: 'Jeudi',
            4: 'Vendredi',
            5: 'Samedi',
            6: 'Dimanche'
        }

        # Convertir la date en jour de la semaine (0 pour lundi, 6 pour dimanche)
        day_of_week = day_of_week_map[date.weekday()]

        _logger.info(" ------------- Check day of week -------- %s", day_of_week)

        # Chercher les disponibilités des enseignants pour ce jour, ce créneau horaire et cette matière
        available_availabilities = self.env['hr.employee.availability'].search([
            ('day_of_week', '=', day_of_week),
            ('start_time', '<=', hour_from),
            ('end_time', '>=', hour_to),
            # ('employee_id.subject_ids', 'in', subject.id)  # Vérifier que l'enseignant enseigne cette matière
        ])

        _logger.info("Available availabilities: %s", available_availabilities)

        available_teachers = []

        # Affichage plus détaillé dans les logs
        for availability in available_availabilities:
            
            # Vérifier si l'enseignant enseigne bien la matière spécifiée
            teacher_subject_lines = self.env['hr.employee.subjects.line'].search([
                ('employee_id', '=', availability.employee_id.id),
                ('subject_id', '=', subject.id)
            ])

            if teacher_subject_lines:
                # Vérifier que l'enseignant n'est pas déjà assigné à un cours à la même période
                conflicting_timetables = self.env['oe.school.timetable'].search([
                    ('teacher_id', '=', availability.employee_id.id),
                    ('date', '=', date),
                    '|',
                    '&', ('hour_from', '<=', hour_from), ('hour_to', '>', hour_from),
                    '&', ('hour_from', '<', hour_to), ('hour_to', '>=', hour_to)
                ])

                if not conflicting_timetables:
                    available_teachers.append(availability.employee_id)
                    _logger.info("Teacher available: %s with priority %s", availability.employee_id.name, availability.employee_id.priority)

        # Trier les enseignants disponibles par priorité (du plus élevé au plus bas)
        available_teachers = sorted(available_teachers, key=lambda t: t.priority, reverse=True)

        # Si aucun enseignant n'est disponible
        # if not available_teachers:
        #     raise UserError(_("Aucun enseignant n'est disponible pour ce créneau horaire et cette matière."))

        # Retourner l'enseignant avec la priorité la plus élevée
        # best_teacher = available_teachers[0]
        # _logger.info("Best teacher found: %s with priority %s", best_teacher.name, best_teacher.priority)
        return available_teachers