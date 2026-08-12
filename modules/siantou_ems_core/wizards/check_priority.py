from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import pytz
import re
import logging

UTC_TZ = pytz.utc

DATE_FORMAT = '%Y-%m-%d'
DATE_FORMAT_FR = '%d/%m/%Y'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATETIME_FORMAT_FR = '%d/%m/%Y %H:%M'
TIME_FORMAT = '%H:%M:%S'
TIME_FORMAT_FR = '%H:%M'

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
            ]).filtered(lambda rec: not (rec.start_time >= end_time or rec.end_time <= start_time))
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
            ]).filtered(lambda rec: not (rec.start_time >= end_time or rec.end_time <= start_time))
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
        sunday_of_week = monday_of_week + timedelta(days=6)

        # Rechercher toutes les lignes d'emploi du temps pour cet enseignant pour cette période (lundi - samedi)
        timetables = self.env['siantou.ems.timetable.timetable'].search([
            ('date', '>=', monday_of_week),
            ('date', '<=', sunday_of_week),
            ('employee_id', '=', employee.id)
        ])

        # Calculer le total des heures assignées pour la semaine
        total_hours = 0
        timetables = list(timetables)
        for timetable in timetables:
            end_time = CheckPriority.convert_float_to_time(timetable.end_time, has_second=True)
            start_time = CheckPriority.convert_float_to_time(timetable.start_time, has_second=True)
            end_time = datetime.strptime(f"{timetable.date} {end_time}", DATETIME_FORMAT)
            start_time = datetime.strptime(f"{timetable.date} {start_time}", DATETIME_FORMAT)

            worked_hours = end_time - start_time
            worked_hours = worked_hours.total_seconds() / 3600.0
            worked_hours = round(worked_hours, 2)

            weekly_hours = weekly_hours - timetable.not_active_slotitems
            if worked_hours < 0.0:
                continue
            total_hours += weekly_hours

        return total_hours

    @staticmethod
    def convert_float_to_time(tm, has_second=False):
        tm = str(tm)
        tm = tm.split('.')
        if len(tm) == 1:
            tm.append('0')
        if len(tm[0]) == 1:
            tm[0] = '0{}'.format(tm[0])
        elif len(tm[0]) > 2:
            tm[0] = '{}'.format(tm[0][0:2])
        if int(tm[0]) > 23:
            tm[0] = '00'
        if len(tm[1]) == 1:
            tm[1] = '{}0'.format(tm[1])
        elif len(tm[1]) > 2:
            tm[1] = '{}'.format(tm[1][0:2])
        if int(tm[1]) > 59:
            tm[1] = '00'
        tm = ':'.join(tm)
        if has_second:
            tm = '{}:00'.format(tm)
        return tm

    @staticmethod
    def convert_time_to_float(tm):
        tm = str(tm)
        tm = tm.split(':')
        tm = tm[0:2]
        tm = '.'.join(tm)
        tm = eval(tm)
        tm = float(tm)
        tm = round(tm, 2)
        return tm
