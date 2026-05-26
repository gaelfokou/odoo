from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from pprint import pformat
import pandas as pd
import numpy as np
import re
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import copy
import logging

DATE_FORMAT = '%Y-%m-%d'
DATE_FORMAT_FR = '%d/%m/%Y'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATETIME_FORMAT_FR = '%d/%m/%Y %H:%M'
TIME_FORMAT = '%H:%M:%S'
TIME_FORMAT_FR = '%H:%M'

STATUS_TIMETABLE = {
    'pending': 'En attente',
    'progress': 'En cours',
    'present': 'Présent',
    'absent': 'Absent',
    'permission': 'Permission',
    'exception': 'Exception',
    'delay': 'Retard',
}

TYPE_COUR = {
    'cj': 'Cours du jour',
    'cs': 'Cours du soir',
}

_logger = logging.getLogger(__name__)

class TeacherDebt(models.Model):
    _name = 'teacher.debt'
    _description = 'Dette d\'enseignant'

    name = fields.Char(
        string='Nom',
    )

    # Enseignant lié à la programmation de cours
    employee_id = fields.Many2one(
        'hr.employee',
        string='Enseignant',
    )

    payment_ids = fields.One2many(
        'teacher.debt.payment',
        'debt_id',
        'Remboursements dette d\'enseignant'
    )

    status = fields.Selection([
            ('pending', 'En attente'),
            ('progress', 'En cours'),
            ('done', 'Terminé'),
        ],
        string='Statut',
        compute='_compute_status',
        store=True
    )

    @api.depends('date')
    def _compute_status(self):
        for record in self:
            if record.date:
                record.status = str(record.date.weekday())
            else:
                record.status = None

    amount = fields.Float(
        'Montant',
        default=0.0,
    )

    def _default_start_date(self):
        start_date = date.today().replace(day=1)
        return start_date

    start_date = fields.Date(
        string='Date de début',
        default=_default_start_date,
    )

    def _default_end_date(self):
        end_date = (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()
        return end_date

    end_date = fields.Date(
        string='Date de fin',
        default=_default_end_date,
    )

    @api.constrains('start_date', 'end_date')
    def _constrains_date(self):
        for record in self:
            if record.start_date > record.end_date:
                raise ValidationError("La date de fin doit être supérieure ou égale à la date de début")

    @api.constrains('amount')
    def _constrains_amount(self):
        for record in self:
            if record.amount <= 0.0:
                raise ValidationError("Le montant doit être supérieur 0")

class TeacherDebtPayment(models.Model):
    _name = 'teacher.debt.payment'
    _description = 'Remboursement dette d\'enseignant'

    name = fields.Char(
        string='Nom',
        compute='_compute_name',
        store=True,
    )

    debt_id = fields.Many2one(
        'teacher.debt',
        'Dette d\'enseignant',
        required=True,
        ondelete='cascade'
    )

    amount = fields.Float(
        'Montant',
        default=0.0,
    )

    date = fields.Datetime(string="Date", default=datetime.now())

    @api.depends('student_id', 'debt_id')
    def _compute_name(self):
        for record in self:
            student_name = record.student_id.name if record.student_id.id else ''
            debt_name = record.debt_id.name if record.debt_id.id else ''
            name = '{} - {}'.format(student_name, debt_name)
            while True:
                if name.startswith(' - '):
                    name = re.sub('^ - ', ' ', name)
                elif name.endswith(' - '):
                    name = re.sub(' - $', ' ', name)
                elif name.find(' -  - ') != -1:
                    name = name.replace(' -  - ', ' - ')
                elif name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

    @api.constrains('amount')
    def _constrains_amount(self):
        for record in self:
            if record.amount <= 0.0:
                raise ValidationError("Le montant doit être supérieur 0")
