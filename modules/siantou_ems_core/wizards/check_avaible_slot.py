import logging

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta, time

_logger = logging.getLogger(__name__)

class CheckAvailableSlot(models.Model):
    _name = 'siantou.ems.timetable.check_available_slot'
    _description = 'Déterminer un creneau pour un cours'

    def find_available_slot(self, current_date, class_id, batch_id, duration_weekly_hours_credit, active_slotitems, not_active_slotitems):
        available_class_slotitems = []
        available_slotitems = []
        available_hours = 0

        nbr_slotitems = len(active_slotitems)

        if nbr_slotitems > 0:
            for start_time, end_time in active_slotitems:
                timetables = self.env['siantou.ems.timetable.timetable'].search([
                    ('class_id', '=', class_id),
                    ('batch_id', '=', batch_id),
                    ('date', '=', current_date),
                ]).filtered(lambda rec: (rec.start_time <= start_time and rec.end_time > start_time) or (rec.start_time < end_time and rec.end_time >= end_time) or \
                    (start_time <= rec.start_time and end_time > rec.start_time) or (start_time < rec.end_time and end_time >= rec.end_time))
                timetables = list(timetables)
                if len(timetables) == 0:
                    available_class_slotitems.append([start_time, end_time])

            nbr_class_slotitems = len(available_class_slotitems)
    
            if nbr_class_slotitems > 0:
                classroom_ids = self.env['siantou.ems.timetable.timetable'].search([
                    ('date', '=', current_date),
                    ('end_time', '=', active_slotitems[nbr_slotitems - 1][1]),
                ]).mapped('classroom_id')
                classroom_ids = classroom_ids.ids
                if len(classroom_ids) > 0:
                    classrooms = self.env['siantou.ems.core.building.classroom'].search([
                        ('id', 'not in', classroom_ids),
                        ('is_cours_active', '=', True),
                    ])
                else:
                    classrooms = self.env['siantou.ems.core.building.classroom'].search([
                        ('is_cours_active', '=', True),
                    ])
                classrooms = list(classrooms)
                for classroom in classrooms:
                    for start_time, end_time in available_class_slotitems:
                        timetables = self.env['siantou.ems.timetable.timetable'].search([
                            ('classroom_id', '=', classroom.id),
                            ('date', '=', current_date),
                        ]).filtered(lambda rec: (rec.start_time <= start_time and rec.end_time > start_time) or (rec.start_time < end_time and rec.end_time >= end_time) or \
                            (start_time <= rec.start_time and end_time > rec.start_time) or (start_time < rec.end_time and end_time >= rec.end_time))
                        timetables = list(timetables)
                        if len(timetables) > 0:
                            continue
                        available_slotitems.append([start_time, end_time, classroom])
                        available_hours = len(available_slotitems)
                        if available_hours == duration_weekly_hours_credit:
                            break
                    if available_hours > 0:
                        break

        available_slot = None

        if available_hours > 0:
            duration_weekly_hours_credit = available_hours
            n = 0
            for not_active_slotitem in not_active_slotitems:
                if available_slotitems[0][0] < not_active_slotitem[1] and available_slotitems[available_hours - 1][1] > not_active_slotitem[0]:
                    n += 1
            available_slot = {'current_date': current_date, 'start_time': available_slotitems[0][0], 'end_time': available_slotitems[available_hours - 1][1], 'classroom': available_slotitems[0][2], 'duration_weekly_hours_credit': duration_weekly_hours_credit, 'not_active_slotitems': n}

        return available_slot
