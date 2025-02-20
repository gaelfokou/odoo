import logging

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta, time

_logger = logging.getLogger(__name__)

class CheckAvailableSlot(models.Model):
    _name = 'siantou.ems.timetable.check_available_slot'
    _description = 'Déterminer un creneau pour un cours'

    def find_available_slot(self, current_date, field_of_study_id, level_id, batch_id, duration_hours_credit=1):
        slots = self.env['siantou.ems.timetable.slot'].search([
            ('is_default', '=', False),
        ])
        slots = list(slots)

        available_slotitem = None
        for slot in slots:
            field_of_study_ids = list(slot.field_of_study_ids)
            for field_of_study in field_of_study_ids:
                if field_of_study.id == field_of_study_id:
                    available_slotitem = slot
                    break
            if available_slotitem:
                break

        if available_slotitem:
            slots = self.env['siantou.ems.timetable.slot'].search([
                ('id', '=', available_slotitem.id),
            ])
        else:
            slots = self.env['siantou.ems.timetable.slot'].search([
                ('is_default', '=', True),
            ])

        slots = list(slots)

        slotitems = []
        for slot in slots:
            slotitem_day_ids = slot.slotitem_day_ids.filtered(lambda s: s.is_active)
            slotitem_day_ids = list(slotitem_day_ids)
            for slotitem_day_id in slotitem_day_ids:
                slotitems.append([round(slotitem_day_id.start_time, 2), round(slotitem_day_id.end_time, 2)])
            slotitem_night_ids = slot.slotitem_night_ids.filtered(lambda s: s.is_active)
            slotitem_night_ids = list(slotitem_night_ids)
            for slotitem_night_id in slotitem_night_ids:
                slotitems.append([round(slotitem_night_id.start_time, 2), round(slotitem_night_id.end_time, 2)])
        slotitems.sort(key=lambda s: s[0])

        available_slotitems = []
        available_hours = 0

        classrooms = self.env['siantou.ems.core.building.classroom'].search([])
        classrooms = list(classrooms)
        for classroom in classrooms:
            for start_time, end_time in slotitems:
                timetables = self.env['siantou.ems.timetable.timetable'].search([
                    ('classroom_id', '=', classroom.id),
                    ('date', '=', current_date),
                    ('start_time', '<', end_time),
                    ('end_time', '>', start_time),
                ])
                timetables = list(timetables)
                if len(timetables) > 0:
                    continue
                available_slotitems.append([start_time, end_time, classroom])
                available_hours = len(available_slotitems)
                if available_hours == duration_hours_credit:
                    break
            if available_hours > 0:
            # if available_hours == duration_hours_credit:
                break
            # else:
            #     available_slotitems = []
            #     available_hours = 0

        available_slot = None

        if available_hours > 0:
        # if available_hours == duration_hours_credit:
            duration_hours_credit = duration_hours_credit - available_hours
            available_slot = {'current_date': current_date, 'start_time': available_slotitems[0][0], 'end_time': available_slotitems[available_hours - 1][1], 'classroom': available_slotitems[0][2], 'duration_hours_credit': duration_hours_credit, 'available_hours': available_hours}

        return available_slot
