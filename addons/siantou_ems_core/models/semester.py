import math

from odoo import models, fields, api
from datetime import timedelta, datetime, date
from odoo.exceptions import ValidationError  # Import the ValidationError class


class Semester(models.Model):
    _name = 'siantou.ems.core.year.semester'
    _description = 'Semestres'

    # Nom du semestre
    name = fields.Char(
        'Nom',
        required=True
    )

    # Date de début de l'année académique
    start_time = fields.Date(
        'Date début',
        required=True
    )

    # Date de fin de l'année académique
    end_time = fields.Date(
        'Date fin',
        required=True
    )

    # Année académique à laquelle est lié le semestre
    year_id = fields.Many2one(
        'siantou.ems.core.year',
        'Année académique',
        help="Année académique à laquelle est lié le semestre",
        required=True,
    )

    # Nombre de semaines dans un semestre
    number_of_week = fields.Integer(
        'Nombre de semaines',
        compute='_compute_number_of_week',
        help='Nombre de semaines sur le semestre',
        store=True
    )

    # Ensemble des cours du semestre
    subject_ids = fields.One2many(
        'siantou.ems.core.subject',
        'semester_id',
        'Cours'
    )

    # Contrainte SQL pour empêcher d'avoir le même nom pour différents semestres
    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Le semestre doit être unique')
    ]

    # Contrainte logique pour empêcher d'avoir des semestres qui se chevauchent
    @api.constrains('start_time', 'end_time')
    def _check_date_overlap(self):
        for record in self:
            if self.search([('id', '!=', record.id), ('start_time', '<=', record.end_time), ('end_time', '>=', record.start_time),]):
                raise ValidationError("Les semestres ne peuvent se supperposer.")

    # Contrainte logique pour s'assurer que la date de fin est supérieure à la date de début
    @api.constrains('start_time', 'end_time')
    def _check_date_are_correct(self):
        for record in self:
            if record.start_time >= record.end_time:
                raise ValidationError("La date de fin doit être supérieure à la date de début.")

    # Fonction pour le champ calculé number_of_week
    @api.depends('start_time', 'end_time')
    def _compute_number_of_week(self):
        for record in self:
            if record.start_time and record.end_time:
                if isinstance(record.start_time, (date, datetime)):
                    start_time_str = record.start_time.strftime('%Y-%m-%d')
                else:
                    start_time_str = record.start_time
                if isinstance(record.end_time, (date, datetime)):
                    end_time_str = record.end_time.strftime('%Y-%m-%d')
                else:
                    end_time_str = record.end_time
                start_time = datetime.strptime(start_time_str, '%Y-%m-%d')
                end_time = datetime.strptime(end_time_str, '%Y-%m-%d')
                diff_days = (end_time - start_time).days
                record.number_of_week = math.ceil(diff_days / 7)
            else:
                record.number_of_week = 0

