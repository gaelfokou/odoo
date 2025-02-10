import logging

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta

_logger = logging.getLogger(__name__)

class CheckPriority(models.Model):
    _name = 'siantou.ems.timetable.check_priority'
    _description = 'Déterminer la priorité d\'un enseignant sur un autre'


    def get_teacher_for_period(self, subject_id, date, start_time, end_time):
        """
        Trouver l'enseignant disponible pour un cours à une période spécifique,
        en priorisant les enseignants permanents, triés par priorité décroissante,
        et en vérifiant que leur quota horaire hebdomadaire n'est pas dépassé
        et qu'ils n'ont pas déjà un cours prévu à la même plage horaire.
        """

        # Étape 1: Chercher les enseignants pour le cours, triés par priorité décroissante
        priorities = self.env['siantou.ems.core.teacher.subject.priority'].search(
            [('subject_id', '=', subject_id)],
            order='priority asc'
        )


        # Chercher les enseignants permanents d'abord
        for priority in priorities:
            teacher = priority.employee_id

            # Étape 2 : Vérifier si l'enseignant a déjà un cours prévu à la même plage horaire
            # overlapping_course = self.env['siantou.ems.timetable.timetable'].search([
            #     ('employee_id', '=', teacher.id),
            #     ('date', '=', date),
            #     ('start_time', '<', end_time),  # Chevauchement d'horaire
            #     ('end_time', '>', start_time)   # Chevauchement d'horaire
            # ], limit=1)

            # if overlapping_course:
            #     continue  # Si l'enseignant a déjà un cours à la même plage horaire, on passe au suivant

            overlapping_courses = self.env['siantou.ems.timetable.timetable'].search([
                ('employee_id', '=', teacher.id),
                ('date', '=', date),
            ]).filtered(lambda rec: (rec.start_time <= start_time and rec.end_time > start_time) or (rec.start_time < end_time and rec.end_time >= end_time))

            overlapping_courses = list(overlapping_courses)

            if len(overlapping_courses) > 0:
                continue  # Si l'enseignant a déjà un cours à la même plage horaire, on passe au suivant

            # Si un enseignant est permanent
            if teacher.is_permanent:
                # Vérifier si le quota horaire hebdomadaire n'est pas atteint
                assigned_hours = self.get_assigned_hours(teacher, date)
                if assigned_hours + (end_time - start_time) > teacher.weekly_hours_limit:
                    continue  # Si le quota est dépassé, on passe au prochain enseignant

                return teacher

        # Chercher les enseignants vacataire
        for priority in priorities:
            teacher = priority.employee_id

            # Étape 2 : Vérifier si l'enseignant a déjà un cours prévu à la même plage horaire
            # overlapping_course = self.env['siantou.ems.timetable.timetable'].search([
            #     ('employee_id', '=', teacher.id),
            #     ('date', '=', date),
            #     ('start_time', '<', end_time),  # Chevauchement d'horaire
            #     ('end_time', '>', start_time)   # Chevauchement d'horaire
            # ], limit=1)

            # if overlapping_course:
            #     continue  # Si l'enseignant a déjà un cours à la même plage horaire, on passe au suivant

            overlapping_courses = self.env['siantou.ems.timetable.timetable'].search([
                ('employee_id', '=', teacher.id),
                ('date', '=', date),
            ]).filtered(lambda rec: (rec.start_time <= start_time and rec.end_time > start_time) or (rec.start_time < end_time and rec.end_time >= end_time))

            overlapping_courses = list(overlapping_courses)

            if len(overlapping_courses) > 0:
                continue  # Si l'enseignant a déjà un cours à la même plage horaire, on passe au suivant

            # Si un enseignant est non permanent
            if not teacher.is_permanent:
                # Vérifier si le quota horaire hebdomadaire n'est pas atteint
                assigned_hours = self.get_assigned_hours(teacher, date)
                if assigned_hours + (end_time - start_time) > teacher.weekly_hours_limit:
                    continue  # Si le quota est dépassé, on passe au prochain enseignant
                                   

                return teacher

        
        # Si aucun enseignant (permanent ou non) n'est disponible
        return None

    # Fonction pour calculer les heures assignées à un enseignant dans la semaine
    def get_assigned_hours(self, employee, date_x):

        # Déterminer le jour de la semaine de date_x (0 = lundi, 6 = dimanche)
        weekday = date_x.weekday()

        # Calculer le lundi de la semaine de date_x
        monday_of_week = date_x - timedelta(days=weekday)

        # Calculer le samedi de la semaine de date_x
        saturday_of_week = monday_of_week + timedelta(days=5)


        # Rechercher toutes les lignes d'emploi du temps pour cet enseignant pour cette période (lundi - samedi)
        timetables = self.env['siantou.ems.timetable.timetable'].search([
            ('date', '>=', monday_of_week),
            ('date', '<=', saturday_of_week),
            ('employee_id', '=', employee.id)
        ])

        # Calculer le total des heures assignées pour la semaine
        total_hours = 0
        for timetable in timetables:
            total_hours += timetable.end_time - timetable.start_time
        
        return total_hours
    