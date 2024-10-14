# -*- coding: utf-8 -*-
import numpy as np
import requests
import json
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta, time
import math

DATE_FORMAT = '%Y-%m-%d'
TIME_FORMAT = '%H:%M'
DATETIME_FORMAT = '%Y-%m-%d %H:%M'

_logger = logging.getLogger(__name__)


class GenerateTimetableWizard(models.TransientModel):
    _name = "oe.school.generatetimetable.wizard"
    _description = 'Assistant pour l\'emploi du temps'

    semester_id = fields.Many2one(
        'oe.school.year.semester',
        string="Semestre",
        required=True
    )

    course_id = fields.Many2one(
        'oe.school.course',
        string="Cursus",
        required=True
    )

    def generate_timetable_(self):
        semester = self.semester_id
        course = self.course_id
        # Récupérer la liste des cours du cursus spécifié liés au semestre spécifié
        courses = self.env['oe.school.course.subject.line'].search([
            ('course_id', '=', course.id)
        ])
        number_of_week = semester.number_of_week
        number_of_day_per_week = 6  # De lundi à samedi
        max_hours_per_day = 7
        max_hours_per_week = number_of_day_per_week * max_hours_per_day

        # Initialisation de l'emploi du temps
        timetable = np.zeros((number_of_week, number_of_day_per_week))
        cours_par_jour = {}

        # Total des heures disponibles dans le semestre
        heures_disponibles_totales = number_of_week * number_of_day_per_week * max_hours_per_day

        # Répartition des cours
        for course in courses:
            volume_horaire = course.volume_horaire
            heures_par_semaine = volume_horaire / number_of_week
            heures_par_jour = heures_par_semaine / number_of_day_per_week

            # Vérifications des contraintes
            if heures_par_semaine > max_hours_per_week:
                raise ValueError(f"Le cours {course.course_id.name} dépasse le nombre d'heures autorisées par semaine.")
            if heures_par_jour > max_hours_per_day:
                raise ValueError(f"Le cours {course.course_id.name} dépasse le nombre d'heures autorisées par jour.")

            # Répartition des heures pour chaque cours
            cours_par_jour[course.course_id.name] = np.full((number_of_week, number_of_day_per_week), heures_par_jour)
            timetable += cours_par_jour[course.course_id.name]

            # Vérifications supplémentaires sur l'emploi du temps
            if np.any(timetable > max_hours_per_day):
                raise ValueError(f"Erreur : dépassement des heures par jour pour le cours {course.course_id.name}.")
            if np.any(np.sum(timetable, axis=1) > max_hours_per_week):
                raise ValueError(f"Erreur : dépassement des heures par semaine pour le cours {course.course_id.name}.")

        # Afficher ou stocker l'emploi du temps
        return timetable, cours_par_jour

    def generate_timetable(self):
        self.env['oe.school.timetable'].search([]).unlink()
        classrooms = self.env['oe.school.building.room'].search([])
        n = len(classrooms)
        semesters = self.env['oe.school.year.semester'].search([
            ('id', '=', self.semester_id.id)
        ])
        # Récupérer la liste des semestres
        for semester in semesters:
            number_of_week = semester.number_of_week
            # Récupérer la liste des cursus
            subjects = self.env['oe.school.subject'].search([])
            for subject in subjects:
                volume_horaire = subject.credit_hour
                if volume_horaire <= 0:
                    continue
                # Récupérer la liste des cours du cursus spécifié liés au semestre spécifié
                course_subjects = self.env['oe.school.course.subject.line'].search([
                    ('subject_id', '=', subject.id)
                ])
                for course_subject in course_subjects:
                    courses = self.env['oe.school.course'].search([
                        ('id', '=', course_subject.course_id.id)
                    ], limit=1)
                    for course in courses:
                        heures_par_semaine = volume_horaire / number_of_week
                        heures_par_semaine = int(math.ceil(heures_par_semaine))
                        date_debut = semester.date_start
                        date_fin = semester.date_end
                        heure_debut_cours = '07:30'
                        heure_fin_cours = '16:00'
                        i = 0
                        while True:
                            if n > i:
                                classroom = classrooms[i]
                                date_debut_string = datetime.strftime(date_debut, DATE_FORMAT)
                                date_fin_string = datetime.strftime(date_fin, DATE_FORMAT)
                                date_heure_debut_cours = datetime.strptime(f'{date_debut_string} {heure_debut_cours}', DATETIME_FORMAT)
                                date_heure_fin_cours = datetime.strptime(f'{date_debut_string} {heure_fin_cours}', DATETIME_FORMAT)
                                if date_heure_fin_cours > (date_heure_debut_cours + timedelta(days=0, hours=heures_par_semaine)):
                                    heure_debut_string = date_heure_debut_cours.strftime(TIME_FORMAT).replace(':', '.')
                                    heure_fin_string = (date_heure_debut_cours + timedelta(days=0, hours=heures_par_semaine)).strftime(TIME_FORMAT).replace(':', '.')
                                    check_cours = self.env['school.room.scheduler'].check_course_for_room(classroom.id, date_debut_string, heure_debut_string, heure_fin_string)
                                    _logger.info(f'----------- tototototototo date_debut_string {date_debut_string} -----------')
                                    _logger.info(f'----------- tototototototo date_heure_debut_cours {heure_debut_string} -----------')
                                    _logger.info(f'----------- tototototototo date_heure_fin_cours {heure_fin_string} -----------')
                                    if check_cours:
                                        i += 1
                                        if n > i:
                                            heure_debut_cours = '07:30'
                                        else:
                                            i = 0
                                            heure_debut_cours = check_cours.hour_to.replace('.', ':')
                                    else:
                                        self.env['oe.school.timetable'].create({
                                            'course_id': course.id,
                                            'subject_id': subject.id,
                                            'classroom_id': classroom.id,
                                            'date': date_debut_string,
                                            'hour_from': date_heure_debut_cours.strftime(TIME_FORMAT).replace(':', '.'),
                                            'hour_to': date_heure_fin_cours.strftime(TIME_FORMAT).replace(':', '.'),
                                        })
                                        break
                                else:
                                    if date_fin > (date_debut + timedelta(days=1)):
                                        date_debut = date_debut + timedelta(days=1)
                                    else:
                                        break
                            else:
                                break

    # def action_create_timetable(self):
    #     # Check if dates are null
    #     if not self.date_start or not self.date_end:
    #         raise UserError(_("Please specify both start date and end date."))
    #
    #     # Check if hours are valid
    #     if not self.hour_from > 0 or not self.hour_to > 0 or self.hour_from >= self.hour_to:
    #         raise UserError(_("Please specify valid hours."))
    #
    #     current_date = self.date_start
    #     end_date = self.date_end
    #
    #     # Récupérer tous les sujets associés au programme
    #     subjects = self.env['oe.school.course.subject.line'].search([('course_id', '=', self.course_id.id)])
    #     if not subjects:
    #         raise UserError(_("Aucun cours trouvé pour le cursus sélectionné."))
    #
    #     # Organiser les sujets sur la semaine
    #     days_of_week = list(range(6))  # [0, 1, 2, 3, 4, 5] (lundi à samedi)
    #     subject_schedule = {}
    #
    #     # Attribuer chaque sujet à un jour de la semaine
    #     for i, subject in enumerate(subjects):
    #         day_index = days_of_week[i % 7]  # Attribue les sujets en boucle sur les 7 jours
    #         if day_index not in subject_schedule:
    #             subject_schedule[day_index] = []
    #         subject_schedule[day_index].append(subject)
    #
    #     # Répéter les mêmes horaires chaque semaine jusqu'à la date de fin
    #     while current_date <= end_date:
    #         current_weekday = current_date.weekday()
    #
    #         # Pour chaque jour de la semaine, vérifier s'il y a des sujets à programmer
    #         if current_weekday in subject_schedule:
    #             for subject in subject_schedule[current_weekday]:
    #                 # Vérifier s'il y a déjà un emploi du temps pour ce sujet et cette journée
    #                 if not self._find_timetable(current_date, subject):
    #                     if self._find_school_time(current_date):
    #                         if not self._find_school_holiday(current_date, self.hour_from, self.hour_to):
    #                             self._create_timetable_records(current_date, subject)
    #
    #         # Passer au jour suivant
    #         current_date += timedelta(days=1)
    #
    #     action = {
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'tree',
    #         'name': _('Timetable'),
    #         'res_model': 'oe.school.timetable',
    #         'view_id': self.env.ref('de_school_timetable.school_timetable_tree_view').id,
    #         # Replace with correct module name
    #     }
    #     return action
    #
    # def _create_timetable_records(self, current_date, subject):
    #     """
    #     Create timetable records for the given day, time range, and subject.
    #     """
    #     self.env['oe.school.timetable'].create({
    #         'course_id': self.course_id.id,
    #         'batch_id': self.batch_id.id,
    #         'subject_id': subject.id,
    #         'teacher_id': self.teacher_id.id,
    #         'user_id': self.user_id.id,
    #         'classroom_id': self.classroom_id.id,
    #         'date': current_date,
    #         'hour_from': self.hour_from,
    #         'hour_to': self.hour_to,
    #     })
    #
    # def _find_timetable(self, current_date, subject):
    #     """
    #     Check if a timetable already exists for the given day and subject.
    #     """
    #     domain = [
    #         ('course_id', '=', self.course_id.id),
    #         ('subject_id', '=', subject.id),
    #         ('date', '=', current_date),
    #     ]
    #     if self.batch_id:
    #         domain += [('batch_id', '=', self.batch_id.id)]
    #     if self.section_id:
    #         domain += [('section_id', '=', self.section_id.id)]
    #
    #     timetable_ids = self.env['oe.school.timetable'].search(domain)
    #     filter_timetable_ids = timetable_ids.filtered(lambda x:
    #                                                   x.hour_from <= self.hour_to
    #                                                   and x.hour_to >= self.hour_from
    #                                                   )
    #     return filter_timetable_ids
