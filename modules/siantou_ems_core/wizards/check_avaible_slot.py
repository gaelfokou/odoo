import logging

from odoo import models, fields, api, tools, _
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

        if len(active_slotitems) > 0:
            for start_time, end_time in active_slotitems:
                timetables = self.env['siantou.ems.timetable.timetable'].search([
                    ('class_id', '=', class_id.id),
                    ('batch_id', '=', batch_id),
                    ('date', '=', current_date),
                ]).filtered(lambda rec: not (rec.start_time >= end_time or rec.end_time <= start_time))
                timetables = list(timetables)
                if len(timetables) == 0:
                    available_class_slotitems.append([start_time, end_time])

            nbr_class_slotitems = len(available_class_slotitems)
    
            if nbr_class_slotitems > 0:
                building_ids = []
                if class_id.filiere_id.school_id:
                    buildings = self.env['siantou.ems.core.building'].search([
                        ('school_ids', 'in', [class_id.filiere_id.school_id.id]),
                    ])
                    building_ids = buildings.ids
                classroom_ids = self.env['siantou.ems.timetable.timetable'].search([
                    ('date', '=', current_date),
                    ('end_time', '=', active_slotitems[-1][1]),
                ]).mapped('classroom_id')
                classroom_ids = classroom_ids.ids
                if len(classroom_ids) > 0:
                    building_classrooms = []
                    building_classroom_ids = []
                    if len(building_ids) > 0:
                        building_classrooms = self.env['siantou.ems.core.building.classroom'].search([
                            ('id', 'not in', classroom_ids),
                            ('is_cours_active', '=', True),
                            ('building_id', 'in', building_ids),
                        ])
                        building_classroom_ids = building_classrooms.ids
                        building_classrooms = list(building_classrooms)
                    if len(building_classroom_ids) > 0:
                        classrooms = self.env['siantou.ems.core.building.classroom'].search([
                            ('id', 'not in', classroom_ids),
                            ('id', 'not in', building_classroom_ids),
                            ('is_cours_active', '=', True),
                        ])
                    else:
                        classrooms = self.env['siantou.ems.core.building.classroom'].search([
                            ('id', 'not in', classroom_ids),
                            ('is_cours_active', '=', True),
                        ])
                    classrooms = list(classrooms)
                else:
                    building_classrooms = []
                    building_classroom_ids = []
                    if len(building_ids) > 0:
                        building_classrooms = self.env['siantou.ems.core.building.classroom'].search([
                            ('is_cours_active', '=', True),
                            ('building_id', 'in', building_ids),
                        ])
                        building_classroom_ids = building_classrooms.ids
                        building_classrooms = list(building_classrooms)
                    if len(building_classroom_ids) > 0:
                        classrooms = self.env['siantou.ems.core.building.classroom'].search([
                            ('id', 'not in', building_classroom_ids),
                            ('is_cours_active', '=', True),
                        ])
                    else:
                        classrooms = self.env['siantou.ems.core.building.classroom'].search([
                            ('is_cours_active', '=', True),
                        ])
                    classrooms = list(classrooms)
                classrooms = building_classrooms + classrooms
                for classroom in classrooms:
                    for start_time, end_time in available_class_slotitems:
                        timetables = self.env['siantou.ems.timetable.timetable'].search([
                            ('classroom_id', '=', classroom.id),
                            ('date', '=', current_date),
                        ]).filtered(lambda rec: not (rec.start_time >= end_time or rec.end_time <= start_time))
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
                if available_slotitems[0][0] < not_active_slotitem[1] and available_slotitems[-1][1] > not_active_slotitem[0]:
                    n += 1
            available_slot = {'current_date': current_date, 'start_time': available_slotitems[0][0], 'end_time': available_slotitems[-1][1], 'classroom': available_slotitems[0][2], 'duration_weekly_hours_credit': duration_weekly_hours_credit, 'not_active_slotitems': n}

        return available_slot
