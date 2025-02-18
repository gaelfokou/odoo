import logging

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta, time

_logger = logging.getLogger(__name__)

class CheckAvailableSlot(models.Model):
    _name = 'siantou.ems.timetable.check_available_slot'
    _description = 'Déterminer un creneau pour un cours'

    def find_available_slot(self, date, field_of_study_id, level_id, batch_id, duration_hours_credit=1):
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

        timetables = self.env['siantou.ems.timetable.timetable'].search([
            ('date', '=', date),
            ('field_of_study_id', '=', field_of_study_id),
            ('level_id', '=', level_id),
            ('batch_id', '=', batch_id)
        ])
        all_timetables = list(timetables)

        available_slotitems = []
        available_slot = None

        if len(all_timetables) > 0:
            for start_time, end_time in slotitems:
                available_timetables = timetables.filtered(lambda rec: (rec.end_time > start_time and rec.start_time <= start_time) or (rec.end_time >= end_time and rec.start_time < end_time))
                available_timetables = list(available_timetables)
                if len(available_timetables) > 0:
                    continue
                available_slotitems.append([start_time, end_time])
                if len(available_slotitems) == duration_hours_credit:
                    break
        else:
            for start_time, end_time in slotitems:
                available_slotitems.append([start_time, end_time])
                if len(available_slotitems) == duration_hours_credit:
                    break

        available_hours = len(available_slotitems)

        if available_hours > 0:
            duration_hours_credit = duration_hours_credit - available_hours
            available_slot = {'date': date, 'start_time': available_slotitems[0][0], 'end_time': available_slotitems[available_hours - 1][1], 'duration_hours_credit': duration_hours_credit, 'available_hours': available_hours}

        return available_slot
