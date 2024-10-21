import logging

from odoo import models, fields, api
from odoo.exceptions import ValidationError

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

    def generate_timetable(self):
        for record in self:
            # Récupérer la liste des filières et les traiter l'une après l'autre
            fields_of_study = self.env['siantou.ems.core.field_of_study'].search([])
            for field in fields_of_study:
                # Récupérer la liste des cours de la filière par niveau et les traiter l'un après l'autre
                subject_ids_by_level = field.get_subject_ids_by_level()
                for level_id, subject_ids in subject_ids_by_level.items():
                    print(f"\n\nNiveau : {level_id}\n\n")
                    print(f"\n\nCours : {subject_ids}\n\n")
                    # Traitement cours par cours de par niveau de la filière
                    for subject_id in subject_ids:
                        print(f"\n\n--- Cours ID : {subject_id}")
                        # On récupère le cours
                        subject = self.env['siantou.ems.core.subject'].browse(subject_id)
                        print(f"--- Cours : {subject}\n\n")
                        print(f"--- Semestre ID : {subject.semester_id.id}\n\n")
                        print(f"--- Record Semestre ID : {record.semester_id.id}\n\n")
                        # On vérifie si le cours est un cours du semestre
                        if subject.semester_id.id == record.semester_id.id:
                            # On initialise weekly_hours_credit pour gérer le nombre de jours sur lesquels on doit programmer le cours
                            weekly_hours_credit = subject.weekly_hours_credit
                            print(f"--- Crédit hebdo : {weekly_hours_credit}\n\n")
                            while weekly_hours_credit > 0:
                                subject_duration = min(4, weekly_hours_credit)
                                # On récupère la liste des enseignants
                                teacher = self.find_available_teacher(subject_id)
                                if teacher['found']:
                                    classroom = self.check_available_classroom(teacher, subject_duration)
                                    if classroom['found']:
                                        self.env['siantou.ems.timetable.timetable'].create({
                                            'semester_id': record.semester_id.id,
                                            'field_of_study_id': field.id,
                                            'level_id': level_id,
                                            'subject_id': subject_id,
                                            'classroom_id': classroom['classroom_id'],
                                            'employee_id': teacher['employee_id'],
                                            'day_of_week': classroom['day_of_week'],
                                            'start_time': classroom['start_time'],
                                            'end_time': classroom['end_time'],
                                        })
                                        weekly_hours_credit -= subject_duration
                                    else:
                                        raise ValidationError("Aucune salle de classe trouvée")
                                        _logger.info('**************** Aucune salle de classe trouvée ****************')
                                else:
                                    raise ValidationError("Aucun professeur trouvé")
                                    _logger.info('**************** Aucun professeur trouvé ****************')
                        else:
                            continue

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

    def check_available_classroom(self, teacher, subject_duration):
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
