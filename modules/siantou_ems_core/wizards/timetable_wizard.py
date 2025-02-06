import logging

from odoo import models, fields, api
from odoo.exceptions import UserError, AccessError, ValidationError
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

        for record in self:
            if record.group:
                new_group = self.env['siantou.ems.timetable.group'].create({'name': record.group})
            else:
                # Génération de la chaîne unique
                unique_string = datetime.now().strftime("%Y%m%d%H%M")
                new_group = self.env['siantou.ems.timetable.group'].create({'name': "group-" + unique_string})

            check_field_of_studies = None
            check_subjects = None
            check_semester_hours_credit = 0
            check_weekly_hours_credit = 0
            check_batches = None
            check_slot = None
            check_teacher = None
            check_classroom = False
            
            # Récupérer la liste des filières et les traiter l'une après l'autre
            field_of_studies = self.env['siantou.ems.core.field_of_study'].search([])
            field_of_studies = list(field_of_studies)
            for field_of_study in field_of_studies:
                check_field_of_studies = field_of_study
                # Récupérer la liste des cours de la filière par niveau et les traiter l'un après l'autre
                subject_ids_by_level = field_of_study.get_subject_ids_by_level()
                for level_id, subject_ids in subject_ids_by_level.items():
                    check_subjects = subject_ids
                    for subject_id in subject_ids:
                        # On récupère le cours
                        subject = self.env['siantou.ems.core.subject'].browse(subject_id)
                        _logger.info(f'----------- tototototototo subject name {subject.name} -----------')
                        _logger.info(f'----------- tototototototo subject weekly_hours_credit {subject.weekly_hours_credit} -----------')
                        if subject.semester_id.id == record.semester_id.id:
                            semester_hours_credit = subject.hours_credit
                            check_semester_hours_credit += semester_hours_credit
                            # On parcours toutes les semaines du semestre
                            for week in range(0, subject.semester_id.number_of_week):
                                # on verifie si le quota semestriel n'est pas atteint
                                if semester_hours_credit > 0:
                                    # On initialise weekly_hours_credit pour gérer le nombre de jours sur lesquels on doit programmer le cours
                                    weekly_hours_credit = subject.weekly_hours_credit
                                    check_weekly_hours_credit += weekly_hours_credit
                                    # On parcours toutes les jours de la semaine
                                    for day in range(0, 6):
                                        # on verifie si le quota hebdomadaire est atteint
                                        if weekly_hours_credit > 0:
                                            start_time = subject.semester_id.start_time - timedelta(days=subject.semester_id.start_time.weekday())
                                            end_time = start_time + timedelta(days=5)
                                            subject_duration = min(4, weekly_hours_credit)
                                            # On parcours les jours de la semaine de Lundi - Samedi
                                            check_available_slot_model = self.env['siantou.ems.timetable.check_available_slot']
                                            target_date = start_time + timedelta(weeks=week, days=day)
                                            batches = self.env['siantou.ems.core.student.batch'].search([
                                                ('school_id', '=', field_of_study.school_id.id),
                                                ('field_of_study_id', '=', field_of_study.id),
                                                ('level_id', '=', level_id),
                                            ])
                                            
                                            for batch in batches:
                                                check_batches = batch
                                                i = 0
                                                duration_hours = subject_duration
                                                while True:
                                                    if duration_hours == 0:
                                                        break
                                                    current_date = target_date + timedelta(days=i)
                                                    current_end_time = current_date - timedelta(days=current_date.weekday())
                                                    current_end_time = current_end_time + timedelta(days=5)
                                                    if current_date > current_end_time:
                                                        i = 0
                                                        target_date = current_end_time + timedelta(days=-current_end_time.weekday(), weeks=1)
                                                        current_date = target_date + timedelta(days=i)
                                                    if current_date > subject.semester_id.end_time:
                                                        break
                                                    available_slot = check_available_slot_model.find_available_slot(current_date, field_of_study.id, level_id, batch.id, duration_hours)
                                                    # Si un créneau est disponible
                                                    if available_slot:
                                                        check_slot = available_slot
                                                        check_available_teacher_model = self.env['siantou.ems.timetable.check_priority']
                                                        # On trouve un enseignant disponible selon sa priorité et son quota horaire
                                                        teacher_priority = check_available_teacher_model.get_teacher_for_period(subject.id, current_date, available_slot["start_time"], available_slot["end_time"])
                                                        if teacher_priority:
                                                            check_teacher = teacher_priority
                                                        # On trouve une salle de classe disponible pour le cours
                                                        classroom = self.check_available_classroom(subject_duration, current_date, day, available_slot["start_time"])
                                                        if classroom['found']:
                                                            check_classroom = classroom['found']
                                                            self.env['siantou.ems.timetable.timetable'].create({
                                                                'semester_id': record.semester_id.id,
                                                                'batch_id': batch.id,
                                                                'field_of_study_id': field_of_study.id,
                                                                'department_id': field_of_study.department_id.id if field_of_study.department_id else None,
                                                                'level_id': level_id,
                                                                'subject_id': subject_id,
                                                                'classroom_id': classroom['classroom_id'],
                                                                'employee_id': teacher_priority.id if teacher_priority else None,
                                                                'date': current_date,
                                                                'day_of_week': str(current_date.weekday()),
                                                                'start_time': available_slot["start_time"],
                                                                'end_time': available_slot["end_time"],
                                                                'group_id': new_group.id,
                                                            })
                                                            duration_hours = available_slot['duration_hours']
                                                            semester_hours_credit -= available_slot['available_hours']
                                                            weekly_hours_credit -= available_slot['available_hours']
                                                        else:
                                                            break
                                                    else:
                                                        i = i + 1

            if not check_field_of_studies:
                raise UserError("Aucune filière trouvée")
            elif not check_subjects:
                raise UserError("Aucun cours trouvé")
            elif check_semester_hours_credit == 0:
                raise UserError("Aucun volume horaire semestriel défini")
            elif check_weekly_hours_credit == 0:
                raise UserError("Aucun volume horaire hebdomadaire défini")
            elif not check_batches:
                raise UserError("Aucun étudiant trouvé")
            elif not check_slot:
                raise UserError("Aucun créneau horaire disponible")
            elif not check_teacher:
                raise UserError("Aucun enseignant disponible")
            elif not check_classroom:
                raise UserError("Aucune salle de classe trouvée")

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

