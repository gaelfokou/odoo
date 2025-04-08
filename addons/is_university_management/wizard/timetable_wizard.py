from odoo import models, fields, api, exceptions


class GenerateTimetableWizard(models.TransientModel):
    _name = 'is.university.school.timetable.wizard'
    _description = 'Wizard pour générer un emploi du temps'

    semester_id = fields.Many2one(
        'is.university.semester',
        string='Semestre',
        required=True
    )

    program_id = fields.Many2one(
        'is.university.school.program',
        string='Programme',
        required=True
    )

    @api.model
    def generate_timetable(self):
        # Étape 1 : Récupérer tous les lots d'étudiants pour le programme et le semestre donnés
        batches = self.env['is.university.school.student.batch'].search([('program_id', '=', self.program_id.id)])

        # Étape 2 : Trier les lots par ordre décroissant d'effectif (taille du lot)
        batches = sorted(batches, key=lambda b: len(b.student_ids), reverse=True)

        # Étape 3 : Récupérer les salles disponibles
        classrooms = self.env['is.university.building.classroom'].search([])

        # Étape 4 : Pour chaque cours du programme et du semestre
        subjects = self.env['is.university.subject'].search([
            ('program_ids', 'in', [self.program_id]),
            ('semester_id', '=', self.semester_id.id)
        ])

        for subject in subjects:
            for batch in batches:
                # Étape 5 : Vérifier la capacité des salles
                suitable_classroom = None
                for classroom in classrooms:
                    if classroom.capacity >= len(batch.student_ids):
                        suitable_classroom = classroom
                        break

                if not suitable_classroom:
                    raise exceptions.UserError("Pas de salle de classe disponible pour le lot {}".format(batch.name))

                # Étape 6 : Attribuer un enseignant disponible
                available_teacher = None
                for teacher in subject.teacher_ids:
                    availability = self._find_teacher_availability(teacher, suitable_classroom)
                    if availability:
                        available_teacher = teacher
                        break

                if not available_teacher:
                    raise exceptions.UserError(
                        "Pas d'enseignant disponible pour le cours {} du lot {}".format(subject.name, batch.name))

                # Étape 7 : Créer l'emploi du temps
                self.create({
                    'program_id': self.program_id.id,
                    'semester_id': self.semester_id.id,
                    'batch_id': batch.id,
                    'subject_id': subject.id,
                    'classroom_id': suitable_classroom.id,
                    'teacher_id': available_teacher.id,
                    'start_time': availability['start_time'],
                    'end_time': availability['end_time']
                })
        return {'type': 'ir.actions.act_window_close'}

    def _find_teacher_availability(self, teacher, classroom):
        # Trouver une disponibilité pour l'enseignant
        for availability in teacher.availability_ids:
            # Vérifier si l'heure et le jour sont compatibles
            if self._is_time_slot_available(availability, classroom):
                return {
                    'start_time': availability.start_time,
                    'end_time': availability.end_time
                }
        return None

    def _is_time_slot_available(self, availability, classroom):
        # Logique pour vérifier si la salle et l'enseignant sont disponibles
        # par exemple, en fonction du jour et des heures disponibles
        # Cela peut inclure la vérification de conflits d'horaires
        # avec d'autres cours dans la même salle ou pour le même enseignant.
        # Simplicité : supposons que la salle est disponible pour cette plage
        return True