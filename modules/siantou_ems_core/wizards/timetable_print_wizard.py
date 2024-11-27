import logging

from odoo import models, fields, api
from odoo.exceptions import UserError
from pprint import pformat
from datetime import datetime, timedelta

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

    # Niveau lié à la programmation de cours
    level_id = fields.Many2one(
        'siantou.ems.core.level',
        'Niveau',
        ondelete='restrict'
    )

    # Ajouter un champ de relation vers hr.department pour lier la filière au département
    department_id = fields.Many2one(
        'hr.department',
        string='Département'
    )

    # Filière liée à la programmation de cours
    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study',
        'Filière',
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

    # Filière liée à la programmation de cours
    group_id = fields.Many2one(
        'siantou.ems.timetable.group',
        'Groupe',
        required=True
    )

    def print_timetable(self):
        # Récupérer les emplois du temps pour le semestre sélectionné
        domain = [
            ('semester_id', '=', self.semester_id.id),
            ('group_id', '=', self.group_id.id)
        ]
        # Ajouter le critère Niveau seulement s'il est sélectionné
        if self.level_id:
            domain.append(('level_id', '=', self.level_id.id))

        # Ajouter le critère Filière seulement s'il est sélectionné
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        
        # Ajouter le critère Filière seulement s'il est sélectionné
        if self.field_of_study_id:
            domain.append(('field_of_study_id', '=', self.field_of_study_id.id))
        
        # Ajouter le critère de période seulement si la période de début et la période de fin sont sélectionnées
        if self.period_from and self.period_to:
            domain.append(('date', '>=', self.period_from))
            domain.append(('date', '<=', self.period_to))

        timetables = self.env['siantou.ems.timetable.timetable'].search(domain)

        # Fonction pour diviser les horaires en segments d'une heure (hours est le nombre d'heure voulu)
        def split_into_hourly_segments(start_time, end_time):
            segments = []
            current_time = start_time
            while current_time < end_time:
                next_time = current_time + timedelta(hours=2)
                # Ne pas dépasser l'heure de fin
                if next_time > end_time:
                    next_time = end_time
                segments.append((current_time, next_time))
                current_time = next_time
            return segments

        # Fonction pour obtenir les dates de début et de fin de la semaine
        def get_week_dates(year, week_number):
            start_date = datetime.strptime(f"{year}-W{week_number}-1", "%Y-W%W-%w")
            end_date = start_date + timedelta(days=6)
            return start_date, end_date

        # Groupement des emplois du temps par filière, niveau, semaine et lot
        grouped_timetables = {}
        for timetable in timetables:
            # Calculer la semaine de l'année et l'année à partir de la date
            year, week_number, _ = timetable.date.isocalendar()  # Récupérer l'année et le numéro de la semaine
            key = (timetable.field_of_study_id.id, timetable.level_id.id, year, week_number, timetable.batch_id.id)  # Ajouter le lot au key

            if key not in grouped_timetables:
                grouped_timetables[key] = []

            # Convertir les heures de début et de fin en chaînes de caractères, si nécessaire
            start_time_str = timetable.start_time if isinstance(timetable.start_time, str) else f"{int(timetable.start_time):02d}:00"
            end_time_str = timetable.end_time if isinstance(timetable.end_time, str) else f"{int(timetable.end_time):02d}:00"

            # Convertir les chaînes d'heures en objets datetime
            start_time = datetime.strptime(start_time_str, '%H:%M')
            end_time = datetime.strptime(end_time_str, '%H:%M')

            # Vérifier si la durée est supérieure à 1 heure
            if (end_time - start_time).seconds > 3600:  # 3600 secondes = 1 heure
                # Diviser les horaires en segments d'une heure
                hourly_segments = split_into_hourly_segments(start_time, end_time)
                for segment_start, segment_end in hourly_segments:
                    grouped_timetables[key].append({
                        'date': timetable.date,
                        'subject_name': timetable.subject_id.name,
                        'subject_code': timetable.subject_id.code,
                        'classroom_name': timetable.classroom_id.name,
                        'building_name': timetable.classroom_id.building_id.name,
                        'batch': timetable.batch_id.name,
                        'day_of_week_number': timetable.day_of_week,
                        'day_of_week': self.convert_number_to_weekday(timetable.day_of_week),
                        'start_time': segment_start.strftime('%H:%M'),  # Formater l'heure
                        'end_time': segment_end.strftime('%H:%M'),      # Formater l'heure
                        'teacher_name': ' '.join(timetable.employee_id.name.split()[:2]) if timetable.employee_id.name else ""
                    })
            else:
                # Ajouter les détails spécifiques de chaque emploi du temps
                grouped_timetables[key].append({
                    'date': timetable.date,
                    'subject_name': timetable.subject_id.name,
                    'subject_code': timetable.subject_id.code,
                    'batch': timetable.batch_id.name,
                    'classroom_name': timetable.classroom_id.name,
                    'building_name': timetable.classroom_id.building_id.name,
                    'day_of_week_number': str(timetable.day_of_week),
                    'day_of_week': self.convert_number_to_weekday(timetable.day_of_week),
                    'start_time': start_time_str,
                    'end_time': end_time_str,
                    'teacher_name': ' '.join(timetable.employee_id.name.split()[:2]) if timetable.employee_id.name else ""
                })

        # Créer un rapport pour chaque filière, niveau, semaine et lot
        report_data = []
        for (field_of_study_id, level_id, year, week_number, batch_id), records in grouped_timetables.items():
            field_of_study = self.env['siantou.ems.core.field_of_study'].browse(field_of_study_id)
            level = self.env['siantou.ems.core.level'].browse(level_id)
            batch = self.env['siantou.ems.core.student.batch'].browse(batch_id)

            # Obtenir les dates de début et de fin de la semaine
            week_start_date, week_end_date = get_week_dates(year, week_number)

            # Vérifier que nous avons bien récupéré des objets valides
            if field_of_study.exists() and level.exists() and batch.exists():
                report_data.append({
                    'semester': self.semester_id.name,
                    'field_of_study': field_of_study.name,
                    'departement': field_of_study.department_id.name,
                    'level': level.name,
                    'batch': batch.name,  # Ajouter le nom du lot
                    'week_number': f"{week_start_date.strftime('%d/%m/%Y')} - {week_end_date.strftime('%d/%m/%Y')}",  # Dates de début et de fin
                    'timetables': records,
                })

        _logger.info('**************** report_data: %s  ****************', pformat(report_data))
        
        # Appeler le rapport PDF
        if not report_data:
            raise UserError("Aucune donnée trouvée.")
        report_action = self.env.ref('siantou_ems_core.action_report_timetable')
        return report_action.report_action(self, data={
                                                    'docdata': {
                                                        'timetable_data': report_data,
                                                        'semester': self.semester_id.name,
                                                        'level': self.level_id.name if self.level_id else "",
                                                        'department': self.department_id.name if self.department_id else "",
                                                        'field_of_study': self.field_of_study_id.name if self.field_of_study_id else ""
                                                    }
                                                })

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