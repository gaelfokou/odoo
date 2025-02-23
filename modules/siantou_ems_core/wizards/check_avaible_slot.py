import logging

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta, time

_logger = logging.getLogger(__name__)

class CheckAvailableSlot(models.Model):
    _name = 'siantou.ems.timetable.check_available_slot'
    _description = 'Déterminer un creneau pour un cours'

    def find_available_slot(self, current_date, class_id, field_of_study_id, batch_id, duration_weekly_hours_credit):
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

        active_slotitems = []
        not_active_slotitems = []
        for slot in slots:
            active_slotitem_day_ids = slot.slotitem_day_ids.filtered(lambda s: s.is_active)
            active_slotitem_day_ids = list(active_slotitem_day_ids)
            for active_slotitem_day_id in active_slotitem_day_ids:
                active_slotitems.append([round(active_slotitem_day_id.start_time, 2), round(active_slotitem_day_id.end_time, 2)])
            active_slotitem_night_ids = slot.slotitem_night_ids.filtered(lambda s: s.is_active)
            active_slotitem_night_ids = list(active_slotitem_night_ids)
            for active_slotitem_night_id in active_slotitem_night_ids:
                active_slotitems.append([round(active_slotitem_night_id.start_time, 2), round(active_slotitem_night_id.end_time, 2)])
            not_active_slotitem_day_ids = slot.slotitem_day_ids.filtered(lambda s: not s.is_active)
            not_active_slotitem_day_ids = list(not_active_slotitem_day_ids)
            for not_active_slotitem_day_id in not_active_slotitem_day_ids:
                not_active_slotitems.append([round(not_active_slotitem_day_id.start_time, 2), round(not_active_slotitem_day_id.end_time, 2)])
            not_active_slotitem_night_ids = slot.slotitem_night_ids.filtered(lambda s: not s.is_active)
            not_active_slotitem_night_ids = list(not_active_slotitem_night_ids)
            for not_active_slotitem_night_id in not_active_slotitem_night_ids:
                not_active_slotitems.append([round(not_active_slotitem_night_id.start_time, 2), round(not_active_slotitem_night_id.end_time, 2)])
        active_slotitems.sort(key=lambda s: s[0])
        not_active_slotitems.sort(key=lambda s: s[0])

        available_class_slotitems = []
        available_slotitems = []
        available_hours = 0

        nbr_slotitems = len(active_slotitems)

        if nbr_slotitems > 0:
            _logger.info(f'----------- tototototototo current_date {current_date} -----------')
            for start_time, end_time in active_slotitems:
                timetable = self.env['siantou.ems.timetable.timetable'].search([
                    ('class_id', '=', class_id),
                    ('batch_id', '=', batch_id),
                    ('date', '=', current_date),
                    ('start_time', '<', end_time),
                    ('end_time', '>', start_time),
                ], limit=1)
                _logger.info(f'----------- tototototototo timetable 1 {timetable} {class_id} {current_date} {start_time} {end_time} -----------')
                if not timetable:
                    available_class_slotitems.append([start_time, end_time])

            nbr_class_slotitems = len(available_class_slotitems)
    
            if nbr_class_slotitems > 0:
                classroom_ids = self.env['siantou.ems.timetable.timetable'].search([
                    ('date', '=', current_date),
                    ('end_time', '=', active_slotitems[nbr_slotitems - 1][1]),
                ]).mapped('classroom_id')
                classroom_ids = classroom_ids.ids
                _logger.info(f'----------- tototototototo classroom_ids {classroom_ids} -----------')
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
                _logger.info(f'----------- tototototototo classrooms {classrooms} -----------')
                for classroom in classrooms:
                    for start_time, end_time in available_class_slotitems:
                        timetable = self.env['siantou.ems.timetable.timetable'].search([
                            ('classroom_id', '=', classroom.id),
                            ('date', '=', current_date),
                            ('start_time', '<', end_time),
                            ('end_time', '>', start_time),
                        ], limit=1)
                        _logger.info(f'----------- tototototototo timetable 2 {timetable} {classroom.id} {current_date} {start_time} {end_time} -----------')
                        if timetable:
                            continue
                        available_slotitems.append([start_time, end_time, classroom])
                        available_hours = len(available_slotitems)
                        if available_hours == duration_weekly_hours_credit:
                            break
                    _logger.info(f'----------- tototototototo available_hours {available_hours} -----------')
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
