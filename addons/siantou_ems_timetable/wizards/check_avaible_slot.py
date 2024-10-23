import logging

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta, time

_logger = logging.getLogger(__name__)

class CheckAvailableSlot(models.Model):
    _name = 'siantou.ems.timetable.check_available_slot'
    _description = 'Déterminer un creneau pour un cours'


    def find_available_slot(self, date, field_of_study_id, level_id, duration_hours=2):
        # Plages horaires disponibles
        available_slots = [(8, 10), (10, 12), (13, 15), (15, 17)]  # (heure de début, heure de fin)
        if duration_hours > 2 :
            available_slots = [(8, 12), (13, 17)]

        # Rechercher tous les cours programmés pour la date donnée, en tenant compte du field_of_study_id et level_id
        scheduled_classes = self.env['siantou.ems.timetable.timetable'].search([
            ('date', '=', date),
            ('field_of_study_id', '=', field_of_study_id),
            ('level_id', '=', level_id)
        ])
      

        # Récupérer les horaires réservés
        reserved_slots = []
        for cls in scheduled_classes:
            
            def float_to_time(float_hour):
                hour = int(float_hour)
                minute = int((float_hour - hour) * 60)
                return time(hour, minute)

            # Utilisation dans votre code
            start_time = float_to_time(cls.start_time)
            end_time = float_to_time(cls.end_time)

            reserved_slots.append((start_time.hour, end_time.hour))  # On récupère juste l'heure

        # Chercher un créneau disponible
        for start_hour, end_hour in available_slots:
            start_time = start_hour
            end_time = start_hour + duration_hours

            # Vérifier si le créneau est dans les heures de disponibilité
            if end_time > end_hour:
                continue  # Ignore si le créneau dépasse la fin de la plage horaire

            # Vérifier si le créneau est réservé
            is_available = True
            for reserved_start, reserved_end in reserved_slots:
                if (start_time < reserved_end and end_time > reserved_start):
                    is_available = False
                    break

            if is_available:
                return {'date': date, 'start_time': start_time, 'end_time': end_time}

        return None  # Aucun créneau disponible
