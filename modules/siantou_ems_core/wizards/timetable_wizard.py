import math
import threading
from odoo import models, fields, api
from odoo.exceptions import UserError, AccessError, ValidationError
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
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

    # Filière liée à la programmation de cours
    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        'Filière',
        ondelete='restrict'
    )

    # Niveau lié à la programmation de cours
    level_id = fields.Many2one(
        'siantou.ems.core.level',
        'Niveau',
        ondelete='restrict'
    )

    # Période de début
    period_from = fields.Date(
        'Période de',
    )

    # Période de fin
    period_to = fields.Date(
        'Période à',
    )

    # Groupe auquel appartient l'emploi du temps
    group = fields.Char(
        'Groupe'
    )

    @api.constrains('period_from', 'period_to')
    def _check_constrains_period(self):
        for record in self:
            if record.period_from > record.period_to:
                raise ValidationError(f"La période de début ne doit pas être supérieure à la période de fin")
            elif record.period_from + relativedelta(months=1) < record.period_to:
                raise ValidationError(f"La plage entre la période de début et la période de fin ne doit pas être supérieure 1 mois")

    def generate_timetable(self):
        # if self.group and self.group.strip() != '':
        #     new_group = self.env['siantou.ems.timetable.group'].create({'name': self.group, 'semester_id': self.semester_id.id})
        # else:
        #     # Génération de la chaîne unique
        #     unique_string = datetime.now().strftime("%Y%m%d%H%M")
        #     new_group = self.env['siantou.ems.timetable.group'].create({'name': "group-" + unique_string, 'semester_id': self.semester_id.id})

        check_classes = None
        check_ues = None
        check_subjects = None
        check_batches = None
        check_semester_hours_credit = 0
        check_weekly_hours_credit = 0
        check_classroom_slot = None
        
        domain = []
        
        if self.level_id.id:
            domain.append(('niveau_id', '=', self.level_id.id))

        # Récupérer la liste des filières et les traiter l'une après l'autre
        if self.field_of_study_id.id:
            domain.append(('filiere_id', '=', self.field_of_study_id.id))

        classes = self.env['siantou.ems.core.class'].search(domain)
        classes = list(classes)
        # Génération de la chaîne unique
        unique_string = datetime.now().strftime("%Y%m%d%H%M")
        for classe in classes:
            check_classes = classe
            if self.group and self.group.strip() != '':
                new_group = self.env['siantou.ems.timetable.group'].create({'name': self.group + "-" + classe.name, 'semester_id': self.semester_id.id})
            else:
                new_group = self.env['siantou.ems.timetable.group'].create({'name': "group-" + unique_string + "-" + classe.name, 'semester_id': self.semester_id.id})

            slots = self.env['siantou.ems.timetable.slot'].search([
                ('is_default', '=', False),
            ])
            slots = list(slots)

            available_slotitem = None
            for slot in slots:
                field_of_study_ids = list(slot.field_of_study_ids)
                for field_of_study in field_of_study_ids:
                    if field_of_study.id == classe.filiere_id.id:
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

            batches = self.env['siantou.ems.core.student.batch'].search([
                ('school_id', '=', classe.filiere_id.school_id.id),
                ('field_of_study_id', '=', classe.filiere_id.id),
                ('level_id', '=', classe.niveau_id.id),
            ])
            batches = list(batches)
            if len(batches) == 0:
                batch = self.env['siantou.ems.core.student.batch'].create_new_batch(classe.filiere_id.school_id.id, classe.filiere_id.id, classe.niveau_id.id)
                batches.append(batch)
            ue_ids = classe.ue_ids.filtered(lambda u: u.semestre_id.id == self.semester_id.id)
            # Récupérer la liste des cours de la filière par niveau et les traiter l'un après l'autre
            ue_ids = list(ue_ids)
            for ue_id in ue_ids:
                check_ues = ue_id
                subject_ids = ue_id.subject_ids.ids
                for subject_id in subject_ids:
                    check_subjects = subject_id
                    for batch in batches:
                        check_batches = batch
                        subject = self.env['siantou.ems.core.subject'].browse(subject_id)
                        semester_hours_credit = subject.hours_credit
                        # on verifie si le quota semestriel est atteint
                        if semester_hours_credit > 0:
                            # On parcours toutes les semaines du semestre
                            for week in range(0, ue_id.semestre_id.number_of_week):
                                # on verifie si le quota semestriel est atteint
                                if semester_hours_credit == 0:
                                    break
                                check_semester_hours_credit += semester_hours_credit
                                # On initialise weekly_hours_credit pour gérer le nombre de jours sur lesquels on doit programmer le cours
                                weekly_hours_credit = math.ceil(subject.hours_credit / ue_id.semestre_id.number_of_week)
                                # on verifie si le quota hebdomadaire est atteint
                                if weekly_hours_credit > 0:
                                    check_weekly_hours_credit += weekly_hours_credit
                                    first_time = ue_id.semestre_id.start_time
                                    if first_time.weekday() == 6:
                                        first_time = first_time + timedelta(days=1)
                                    start_time = first_time - timedelta(days=first_time.weekday())
                                    end_time = start_time + timedelta(days=5)
                                    weekly_hours_credit = min(4, weekly_hours_credit)
                                    # On parcours toutes les jours de la semaine
                                    for day in range(0, end_time.weekday() + 1):
                                        if week == 0:
                                            if day < first_time.weekday():
                                                continue
                                        # on verifie si le quota hebdomadaire est atteint
                                        if weekly_hours_credit == 0:
                                            break
                                        # On parcours les jours de la semaine de Lundi - Samedi
                                        target_date = start_time + timedelta(weeks=week, days=day)
                                        if self.period_from and self.period_to:
                                            if self.period_from > target_date or self.period_to < target_date:
                                                continue
                                        available_slot = self.env['siantou.ems.timetable.check_available_slot'].find_available_slot(target_date, classe.id, batch.id, weekly_hours_credit, active_slotitems, not_active_slotitems)
                                        # On trouve une salle de classe et un créneau horaire disponiblent pour le cours
                                        if available_slot:
                                            check_classroom_slot = available_slot
                                            # On trouve un enseignant disponible selon sa priorité et son quota horaire
                                            teacher_priority = self.env['siantou.ems.timetable.check_priority'].get_teacher_for_period(subject.id, target_date, available_slot["start_time"], available_slot["end_time"], available_slot['not_active_slotitems'])
                                            if teacher_priority:
                                                teacher_priority = self.find_available_teacher(teacher_priority, target_date, available_slot["start_time"], available_slot["end_time"])
                                            self.env['siantou.ems.timetable.timetable'].create({
                                                'semester_id': ue_id.semestre_id.id,
                                                'batch_id': batch.id,
                                                'class_id': classe.id,
                                                'department_id': classe.filiere_id.department_id.id,
                                                'subject_id': subject_id,
                                                'classroom_id': available_slot["classroom"].id,
                                                'employee_id': teacher_priority.id if teacher_priority else None,
                                                'date': target_date,
                                                'day_of_week': str(target_date.weekday()),
                                                'start_time': available_slot["start_time"],
                                                'end_time': available_slot["end_time"],
                                                'not_active_slotitems': available_slot['not_active_slotitems'],
                                                'group_id': new_group.id,
                                            })
                                            self.env.cr.commit()
                                            duration_weekly_hours_credit = available_slot['duration_weekly_hours_credit']
                                            semester_hours_credit -= duration_weekly_hours_credit
                                            weekly_hours_credit -= duration_weekly_hours_credit
                                else:
                                    break
                        else:
                            break

        if not check_classes:
            raise UserError("Aucune classe trouvée")
        elif not check_ues:
            raise UserError("Aucun unité d'enseignement trouvé")
        elif not check_subjects:
            raise UserError("Aucun cours trouvé")
        elif not check_batches:
            raise UserError("Aucun étudiant trouvé")
        elif check_semester_hours_credit == 0:
            raise UserError("Aucun volume horaire semestriel trouvé")
        elif check_weekly_hours_credit == 0:
            raise UserError("Aucun volume horaire hebdomadaire trouvé")
        elif not check_classroom_slot:
            raise UserError("Aucune salle de classe et/ou créneau horaire trouvé")

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def find_available_teacher(self, teacher, date, start_time, end_time):
        availabilities = teacher.teacher_availability_ids.filtered(lambda rec: (rec.day_of_week == str(date.weekday())) and ((rec.start_time <= start_time and rec.end_time > start_time) and (rec.start_time < end_time and rec.end_time >= end_time)))

        availabilities = list(availabilities)

        if len(availabilities) > 0:
            return teacher

        return None
