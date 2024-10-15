from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class SchoolRoomScheduler(models.Model):
    _name = 'school.room.scheduler'
    _description = 'Room Scheduler for Courses'

    @api.model
    def check_course_for_room(self, classroom_id, date, hour_from, hour_to):
        hour_from = float(hour_from)
        hour_to = float(hour_to)
        """
        Vérifie s'il y a un cours prévu pour une salle donnée à une date spécifique 
        et dans un intervalle horaire défini par hour_from et hour_to.

        :param classroom_id: ID de la salle
        :param date: Date du jour (format Date)
        :param hour_from: Heure de début (float)
        :param hour_to: Heure de fin (float)
        :return: True si un cours est prévu, False sinon
        """
        _logger.info(f'----------- tototototototo classroom_id {classroom_id} -----------')
        _logger.info(f'----------- tototototototo date {date} -----------')
        _logger.info(f'----------- tototototototo hour_from {hour_from} -----------')
        _logger.info(f'----------- tototototototo hour_to {hour_to} -----------')
        # Recherche dans la table 'oe.school.timetable'
        timetable_obj = self.env['oe.school.timetable']
        overlapping_courses = timetable_obj.search([
            ('classroom_id', '=', classroom_id),
            ('date', '=', date),
            ('hour_from', '<', hour_to),  # Le début du cours est avant la fin de la plage
            ('hour_to', '>', hour_from)   # La fin du cours est après le début de la plage
        ])

        _logger.info(f'----------- tototototototo len {len(overlapping_courses)} -----------')
        if len(overlapping_courses) > 0:
            # raise UserError(_("Un cours est déjà prévu dans cette salle entre %s et %s à la date %s.") % (hour_from, hour_to, date))
            return True  # Un cours est déjà prévu dans cette salle
        
        return False  # Pas de conflit avec les autres cours

    