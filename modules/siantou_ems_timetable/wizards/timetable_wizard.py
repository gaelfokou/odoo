import logging

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)
class TimetableWizard(models.TransientModel):
    _name = 'siantou.ems.timetable.timetable_wizard'
    _description = 'Assistant de génération automatique de l\'emploi du temps'

    # Semestre pour lequel on souhaite tirer l'emploi du temps
    semester_id = fields.Many2one(
        'siantou.ems.core.year.semester',
        'Semester',
        required=True
    )

    # Groupe auquel appartient l'emploi du temps
    group = fields.Char(
        'Groupe'
    )


    def generate_timetable(self):
        _logger.info(' ___________________________________generate___________________________________________________ ')

        for record in self:
            if record.group:
                new_group = self.env['siantou.ems.timetable.group'].create({'name': record.group})
            else:
                # Génération de la chaîne unique
                unique_string = datetime.now().strftime("%Y%m%d%H%M")
                new_group = self.env['siantou.ems.timetable.group'].create({'name': "group-" + unique_string})
            
            _logger.info(' ___________________________________generate 1___________________________________________________ ')
            # Récupérer la liste des filières et les traiter l'une après l'autre
            fields_of_study = self.env['siantou.ems.core.field_of_study'].search([])
            # SI la liste des filières est vide signaler qu'il n'ya pas de filières
            if len(fields_of_study) == 0:
                raise ValidationError("Aucune filière trouvée")
            for field in fields_of_study:
                _logger.info(' ___________________________________generate department_id ___________________________________________________ %s ', field.department_id.id)
                # Récupérer la liste des cours de la filière par niveau et les traiter l'un après l'autre
                subject_ids_by_level = field.get_subject_ids_by_level()
                for level_id, subject_ids in subject_ids_by_level.items():
                    batches = self.env['siantou.ems.core.student.batch'].search([
                        ('school_id', '=', field.school_id.id),
                        ('field_of_study_id', '=', field.id),
                        ('level_id', '=', level_id),
                    ])
                    _logger.info(' ___________________________________generate FIELD1 ___________________________________________________ %s ', field.id)
                    
                    for batch in batches:
                        for subject_id in subject_ids:
                            # On récupère le cours
                            _logger.info(' ___________________________________generate FIELD2 ___________________________________________________ %s ', field.id)
                            subject = self.env['siantou.ems.core.subject'].browse(subject_id)
                            if subject.semester_id.id == record.semester_id.id:
                                _logger.info(' ___________________________________generate FIELD3 ___________________________________________________ %s ', field.id)
                                semester_hours_credit = subject.hours_credit
                                # On parcours toutes les semaines du semestre
                                for week in range(1, subject.semester_id.number_of_week + 1):
                                    _logger.info(' ___________________________________generate FIELD4 ___________________________________________________ %s ', field.id)
                                    # on verifie si le quota semestriel n'est pas atteint
                                    if semester_hours_credit > 0:
                                        # On initialise weekly_hours_credit pour gérer le nombre de jours sur lesquels on doit programmer le cours
                                        weekly_hours_credit = subject.weekly_hours_credit
                                        # On parcours les jours de la semaine de Lundi - Samedi
                                        for day in range(0, 6):
                                            # on verifie si le quota hebdomadaire est atteint
                                            if weekly_hours_credit > 0:
                                                subject_duration = min(4, weekly_hours_credit)
                                                check_available_slot_model = self.env['siantou.ems.timetable.check_available_slot']
                                                target_date = subject.semester_id.start_time + timedelta(weeks=week - 1, days=day)
                                                available_slot = check_available_slot_model.find_available_slot(target_date, field.id, level_id, subject_duration)
                                                # Si un crénau est disponible
                                                if available_slot:
                                                    _logger.info(' ______________________________________________________________________________________ ')
                                                    _logger.info(' ++++++++++++++++++++++++++++ Crénau trouvé !!!!! %s++++++++++++++++++++++++++++++ ', available_slot)
                                                    check_available_teacher_model = self.env['siantou.ems.timetable.check_priority']
                                                    # On trouve un enseignant disponible selon sa priorité et son quota horaire
                                                    teacher_priority = check_available_teacher_model.get_teacher_for_period(subject.id, target_date, day, available_slot["start_time"], available_slot["end_time"], week)
                                                    if not teacher_priority:
                                                        _logger.info(' ++++++++++++++++++++++++++++ Aucun Enseignant trouvé poyur ce crenau !!!!! %s++++++++++++++++++++++++++++++ ', available_slot)
                                                    # On trouve une salle de classe disponible pour le cours
                                                    classroom = self.check_available_classroom(subject_duration, target_date, day, available_slot["start_time"])
                                                    _logger.info('**************** Salle de classe **************** %s %s %s %s %s %s', 
                                                                 classroom['found'], classroom['classroom_id'], classroom['day_of_week'],
                                                                   classroom['start_time'], classroom['end_time'], classroom['date'])
                                                    if classroom['found']:
                                                        self.env['siantou.ems.timetable.timetable'].create({
                                                            'semester_id': record.semester_id.id,
                                                            'batch_id': batch.id,
                                                            'field_of_study_id': field.id,
                                                            'department_id': field.department_id.id if field.department_id else False,
                                                            'level_id': level_id,
                                                            'subject_id': subject_id,
                                                            'classroom_id': classroom['classroom_id'],
                                                            'employee_id': teacher_priority.id if teacher_priority else False,
                                                            'date': target_date,
                                                            'day_of_week': str(day),
                                                            'start_time': available_slot["start_time"],
                                                            'end_time': available_slot["end_time"],
                                                            'group_id': new_group.id,
                                                        })
                                                        weekly_hours_credit -= subject_duration
                                                        semester_hours_credit -= subject_duration
                                                    else:
                                                        _logger.info('**************** Aucune salle de classe trouvée ****************')
                                                else:
                                                    _logger.info('**************** Aucun crénau horaire disponible ****************')
                
    def find_available_teacher(self, subject_id):
        subject = self.env['siantou.ems.core.subject'].browse(subject_id)
        teachers = subject.teacher_ids
        for teacher in teachers:
            availabilities = teacher.teacher_availability_ids
            for availability in availabilities:
                conflicting_timetables = self.env['siantou.ems.timetable.timetable'].search([
                    ('employee_id', '=', teacher.id),
                    ('day_of_week', '=', availability.day_of_week),
                    ('start_time', '<', availability.end_time),
                    ('end_time', '>', availability.start_time),
                ])
                if not conflicting_timetables:
                    return {
                        'found': True,
                        'employee_id': teacher.id,
                        'day_of_week': availability.day_of_week,
                        'start_time': availability.start_time,
                    }
        return {
            'found': False,
        }

    def check_available_classroomOld(self, teacher, subject_duration):
        available_classrooms = self.env['siantou.ems.core.building.classroom'].search([])
        for classroom in available_classrooms:
            conflicting_timetables = self.env['siantou.ems.timetable.timetable'].search([
                ('classroom_id', '=', classroom.id),
                ('day_of_week', '=', teacher['day_of_week']),
                ('start_time', '<', teacher['start_time'] + subject_duration),
                ('end_time', '>', teacher['start_time']),
            ])
            if not conflicting_timetables:
                return {
                    'found': True,
                    'classroom_id': classroom.id,
                    'day_of_week': teacher['day_of_week'],
                    'start_time': teacher['start_time'],
                    'end_time': teacher['start_time'] + subject_duration,
                }
        return {
            'found': False,
        }

    def check_available_classroom(self, subject_duration, date, day_of_week, start_time):
        available_classrooms = self.env['siantou.ems.core.building.classroom'].search([])
        for classroom in available_classrooms:
            conflicting_timetables = self.env['siantou.ems.timetable.timetable'].search([
                ('classroom_id', '=', classroom.id),
                ('date', '=', date),
                ('day_of_week', '=', day_of_week),
                ('start_time', '<', start_time + subject_duration),
                ('end_time', '>', start_time),
            ])
            if not conflicting_timetables:
                return {
                    'found': True,
                    'classroom_id': classroom.id,
                    'date': date,
                    'day_of_week': day_of_week,
                    'start_time': start_time,
                    'end_time': start_time + subject_duration,
                }
        return {
            'found': False,
        }

