import logging

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
class TimetablePrintWizard(models.TransientModel):
    _name = 'siantou.ems.timetable.timetable_print_wizard'
    _description = 'Assistant d\'impression de l\'emploi du temps'

    # Semestre pour lequel on souhaite tirer l'emploi du temps
    semester_id = fields.Many2one(
        'siantou.ems.core.year.semester',
        'Semester',
        required=True
    )

    def print_timetable(self):
        # Récupérer les emplois du temps pour le semestre sélectionné
        timetables = self.env['siantou.ems.timetable.timetable'].search([
            ('semester_id', '=', self.semester_id.id)
        ])

        # Groupement des emplois du temps par filière et niveau
        grouped_timetables = {}
        for timetable in timetables:
            key = (timetable.field_of_study_id.id, timetable.level_id.id)
            if key not in grouped_timetables:
                grouped_timetables[key] = []
            # Ajouter les détails spécifiques de chaque emploi du temps
            grouped_timetables[key].append({
                'subject_name': timetable.subject_id.name,
                'classroom_name': timetable.classroom_id.name,
                'day_of_week': self.convert_number_to_weekday(timetable.day_of_week),
                'start_time': timetable.start_time,
                'end_time': timetable.end_time,
                'teacher_name': timetable.employee_id.name
            })

        # Créer un rapport pour chaque filière et niveau
        report_data = []
        for (field_of_study_id, level_id), records in grouped_timetables.items():
            field_of_study = self.env['siantou.ems.core.field_of_study'].browse(field_of_study_id)
            level = self.env['siantou.ems.core.level'].browse(level_id)

            # Vérifier que nous avons bien récupéré des objets valides
            if field_of_study.exists() and level.exists():
                report_data.append({
                    'semester': self.semester_id.name,
                    'field_of_study': field_of_study.name,
                    'level': level.name,
                    'timetables': records,
                })

        # Appeler le rapport PDF
        if not report_data:
            raise UserError("Aucune donnée trouvée.")
        report_action = self.env.ref('siantou_ems_timetable.action_report_timetable')
        return report_action.report_action(self, data={'docdata': {'timetable_data': report_data}})

    def convert_number_to_weekday(self, number):
        if number == '0':
            return "Lundi"
        if number == '1':
            return "Mardi"
        if number == '2':
            return "Mercredi"
        if number == '3':
            return "Jeudi"
        if number == '4':
            return "Vendredi"
        if number == '5':
            return "Samedi"