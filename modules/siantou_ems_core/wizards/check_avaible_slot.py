import logging

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta, time

_logger = logging.getLogger(__name__)

class CheckAvailableSlot(models.Model):
    _name = 'siantou.ems.timetable.check_available_slot'
    _description = 'Déterminer un creneau pour un cours'

    def find_available_slot(self, current_date, field_of_study_id, level_id, batch_id, duration_weekly_hours_credit):
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

        all_classrooms = self.env['siantou.ems.core.building.classroom'].search([])
        all_classroom_ids = all_classrooms.ids
        if len(all_classroom_ids) > 0:
            for start_time, end_time in slotitems:
                classroom_ids = self.env['siantou.ems.timetable.timetable'].search([
                    ('classroom_id', 'in', all_classroom_ids),
                    ('date', '=', current_date),
                    ('start_time', '<', end_time),
                    ('end_time', '>', start_time),
                ]).mapped('classroom_id')
                classroom_ids = classroom_ids.ids
                if len(classroom_ids) > 0:
                    classrooms = self.env['siantou.ems.core.building.classroom'].search([
                        ('id', 'not in', classroom_ids),
                    ])
                else:
                    classrooms = self.env['siantou.ems.core.building.classroom'].search([
                        ('id', 'in', all_classroom_ids),
                    ])
                classrooms = list(classrooms)
                if len(classrooms) == 0:
                    continue
                timetable = self.env['siantou.ems.timetable.timetable'].search([
                    ('date', '=', current_date),
                    ('start_time', '<', end_time),
                    ('end_time', '>', start_time),
                    ('field_of_study_id', '=', field_of_study_id),
                    ('level_id', '=', level_id),
                    ('batch_id', '=', batch_id)
                ], limit=1)
                if timetable:
                    continue
                available_slotitems.append([start_time, end_time, classrooms[0]])
                available_hours = len(available_slotitems)
                if available_hours == duration_weekly_hours_credit:
                    break

        available_slot = None

        if available_hours > 0:
            duration_weekly_hours_credit = available_hours
            available_slot = {'current_date': current_date, 'start_time': available_slotitems[0][0], 'end_time': available_slotitems[available_hours - 1][1], 'classroom': available_slotitems[0][2], 'duration_weekly_hours_credit': duration_weekly_hours_credit}

        return available_slot
