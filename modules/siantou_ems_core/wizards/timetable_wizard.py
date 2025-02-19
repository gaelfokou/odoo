import math

from odoo import models, fields, api
from odoo.exceptions import UserError, AccessError, ValidationError
from datetime import datetime, timedelta
import logging

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
                new_group = self.env['siantou.ems.timetable.group'].create({'name': record.group, 'semester_id': record.semester_id.id})
            else:
                # Génération de la chaîne unique
                unique_string = datetime.now().strftime("%Y%m%d%H%M")
                new_group = self.env['siantou.ems.timetable.group'].create({'name': "group-" + unique_string, 'semester_id': record.semester_id.id})

            check_classes = None
            check_subjects = None
            check_semester_hours_credit = 0
            check_weekly_hours_credit = 0
            check_batches = None
            check_classroom_slot = None
            
            # Récupérer la liste des filières et les traiter l'une après l'autre
            classes = self.env['siantou.ems.core.class'].search([])
            classes = list(classes)
            for classe in classes:
                field_of_study = classe.filiere_id
                check_classes = field_of_study
                level_id = classe.niveau_id.id
                ue_ids = classe.ue_ids.filtered(lambda u: u.semestre_id.id == record.semester_id.id)
                # Récupérer la liste des cours de la filière par niveau et les traiter l'un après l'autre
                ue_ids = list(ue_ids)
                for ue_id in ue_ids:
                    subject_ids = ue_id.subject_ids.ids
                    for subject_id in subject_ids:
                        check_subjects = subject_id
                        # On récupère le cours
                        subject = self.env['siantou.ems.core.subject'].browse(subject_id)
                        batches = self.env['siantou.ems.core.student.batch'].search([
                            ('school_id', '=', field_of_study.school_id.id),
                            ('field_of_study_id', '=', field_of_study.id),
                            ('level_id', '=', level_id),
                        ])
                        batches = list(batches)
                        if len(batches) == 0:
                            batch = self.env['siantou.ems.core.student.batch'].create_new_batch(field_of_study.school_id.id, field_of_study.id, level_id)
                            batches.append(batch)
                        for batch in batches:
                            check_batches = batch
                            semester_hours_credit = subject.hours_credit
                            check_semester_hours_credit += semester_hours_credit
                            # On parcours toutes les semaines du semestre
                            for week in range(0, record.semester_id.number_of_week):
                                # on verifie si le quota semestriel n'est pas atteint
                                if semester_hours_credit > 0:
                                    # On initialise weekly_hours_credit pour gérer le nombre de jours sur lesquels on doit programmer le cours
                                    weekly_hours_credit = math.ceil(subject.hours_credit / record.semester_id.number_of_week)
                                    check_weekly_hours_credit += weekly_hours_credit
                                    # On parcours toutes les jours de la semaine
                                    for day in range(0, 6):
                                        # on verifie si le quota hebdomadaire est atteint
                                        if weekly_hours_credit > 0:
                                            start_time = record.semester_id.start_time - timedelta(days=record.semester_id.start_time.weekday())
                                            end_time = start_time + timedelta(days=5)
                                            duration_hours_credit = min(4, weekly_hours_credit)
                                            # On parcours les jours de la semaine de Lundi - Samedi
                                            check_available_slot_model = self.env['siantou.ems.timetable.check_available_slot']
                                            target_date = start_time + timedelta(weeks=week, days=day)
                                            i = 0
                                            while True:
                                                if duration_hours_credit == 0:
                                                    break
                                                current_date = target_date + timedelta(days=i)
                                                current_end_time = current_date - timedelta(days=current_date.weekday())
                                                current_end_time = current_end_time + timedelta(days=5)
                                                if current_date > current_end_time:
                                                    i = 0
                                                    target_date = current_end_time + timedelta(days=-current_end_time.weekday(), weeks=1)
                                                    current_date = target_date + timedelta(days=i)
                                                if current_date > record.semester_id.end_time:
                                                    break
                                                available_slot = check_available_slot_model.find_available_slot(current_date, field_of_study.id, level_id, batch.id, duration_hours_credit)
                                                # On trouve une salle de classe et un créneau horaire disponiblent pour le cours
                                                if available_slot:
                                                    check_classroom_slot = available_slot
                                                    check_available_teacher_model = self.env['siantou.ems.timetable.check_priority']
                                                    # On trouve un enseignant disponible selon sa priorité et son quota horaire
                                                    teacher_priority = check_available_teacher_model.get_teacher_for_period(subject.id, current_date, available_slot["start_time"], available_slot["end_time"])
                                                    if teacher_priority:
                                                        teacher_priority = self.find_available_teacher(teacher_priority, current_date, available_slot["start_time"], available_slot["end_time"])
                                                    timetables = self.env['siantou.ems.timetable.timetable'].search([
                                                        ('classroom_id', '=', available_slot["classroom"].id),
                                                        ('date', '=', current_date),
                                                        ('start_time', '<', available_slot["end_time"]),
                                                        ('end_time', '>', available_slot["start_time"]),
                                                    ])
                                                    timetables = list(timetables)
                                                    if len(timetables) == 0:
                                                        self.env['siantou.ems.timetable.timetable'].create({
                                                            'semester_id': record.semester_id.id,
                                                            'batch_id': batch.id,
                                                            'field_of_study_id': field_of_study.id,
                                                            'department_id': field_of_study.department_id.id if field_of_study.department_id else None,
                                                            'level_id': level_id,
                                                            'subject_id': subject_id,
                                                            'classroom_id': available_slot["classroom"].id,
                                                            'employee_id': teacher_priority.id if teacher_priority else None,
                                                            'date': current_date,
                                                            'day_of_week': str(current_date.weekday()),
                                                            'start_time': available_slot["start_time"],
                                                            'end_time': available_slot["end_time"],
                                                            'group_id': new_group.id,
                                                        })
                                                        duration_hours_credit = available_slot['duration_hours_credit']
                                                        semester_hours_credit -= available_slot['available_hours']
                                                        weekly_hours_credit -= available_slot['available_hours']
                                                else:
                                                    break
                                            else:
                                                i = i + 1

            if not check_classes:
                raise UserError("Aucune classe trouvée")
            elif not check_subjects:
                raise UserError("Aucun cours trouvé")
            elif not check_batches:
                raise UserError("Aucun étudiant trouvé")
            elif check_semester_hours_credit == 0:
                raise UserError("Aucun volume horaire semestriel défini")
            elif check_weekly_hours_credit == 0:
                raise UserError("Aucun volume horaire hebdomadaire défini")
            elif not check_classroom_slot:
                raise UserError("Aucune salle de classe et créneau horaire disponiblent")

    def find_available_teacher(self, teacher, date, start_time, end_time):
        availabilities = teacher.teacher_availability_ids.filtered(lambda rec: (rec.day_of_week == str(date.weekday())) and ((rec.start_time <= start_time and rec.end_time > start_time) and (rec.start_time < end_time and rec.end_time >= end_time)))

        availabilities = list(availabilities)

        if len(availabilities) > 0:
            return teacher

        return None
