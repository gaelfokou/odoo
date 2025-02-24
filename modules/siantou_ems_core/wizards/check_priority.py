from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

class CheckPriority(models.Model):
    _name = 'siantou.ems.timetable.check_priority'
    _description = 'Déterminer la priorité d\'un enseignant sur un autre'


    def get_teacher_for_period(self, subject_id, date, start_time, end_time, not_active_slotitems):
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

            timetables = self.env['siantou.ems.timetable.timetable'].search([
                ('employee_id', '=', teacher.id),
                ('date', '=', date),
            ]).filtered(lambda rec: (rec.start_time <= start_time and rec.end_time > start_time) or (rec.start_time < end_time and rec.end_time >= end_time) or \
                (start_time <= rec.start_time and end_time > rec.start_time) or (start_time < rec.end_time and end_time >= rec.end_time))
            timetables = list(timetables)
            if len(timetables) > 0:
                continue  # Si l'enseignant a déjà un cours à la même plage horaire, on passe au suivant

            # Si un enseignant est permanent
            if teacher.is_permanent:
                # Vérifier si le quota horaire hebdomadaire n'est pas atteint
                assigned_hours = self.get_assigned_hours(teacher, date)
                total_hours = end_time - start_time
                total_hours = total_hours - not_active_slotitems
                if assigned_hours + total_hours > teacher.weekly_hours_limit:
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

            timetables = self.env['siantou.ems.timetable.timetable'].search([
                ('employee_id', '=', teacher.id),
                ('date', '=', date),
            ]).filtered(lambda rec: (rec.start_time <= start_time and rec.end_time > start_time) or (rec.start_time < end_time and rec.end_time >= end_time) or \
                (start_time <= rec.start_time and end_time > rec.start_time) or (start_time < rec.end_time and end_time >= rec.end_time))
            timetables = list(timetables)
            if len(timetables) > 0:
                continue  # Si l'enseignant a déjà un cours à la même plage horaire, on passe au suivant

            # Si un enseignant est non permanent
            if not teacher.is_permanent:
                # Vérifier si le quota horaire hebdomadaire n'est pas atteint
                assigned_hours = self.get_assigned_hours(teacher, date)
                total_hours = end_time - start_time
                total_hours = total_hours - not_active_slotitems
                if assigned_hours + total_hours > teacher.weekly_hours_limit:
                    continue  # Si le quota est dépassé, on passe au prochain enseignant
                                   

                return teacher

        
        # Si aucun enseignant (permanent ou non) n'est disponible
        return None

    # Fonction pour calculer les heures assignées à un enseignant dans la semaine
    def get_assigned_hours(self, employee, date):

        monday_of_week = date - timedelta(days=date.weekday())
        saturday_of_week = monday_of_week + timedelta(days=5)

        # Rechercher toutes les lignes d'emploi du temps pour cet enseignant pour cette période (lundi - samedi)
        timetables = self.env['siantou.ems.timetable.timetable'].search([
            ('date', '>=', monday_of_week),
            ('date', '<=', saturday_of_week),
            ('employee_id', '=', employee.id)
        ])

        # Calculer le total des heures assignées pour la semaine
        total_hours = 0
        timetables = list(timetables)
        for timetable in timetables:
            total_hours += timetable.end_time - timetable.start_time
            total_hours = total_hours - timetable.not_active_slotitems

        return total_hours
