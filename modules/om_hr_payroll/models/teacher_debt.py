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

TYPE_COUR = {
    'cj': 'Cours du jour',
    'cs': 'Cours du soir',
}

_logger = logging.getLogger(__name__)

class TeacherDebt(models.Model):
    _name = 'teacher.debt'
    _description = 'Dette d\'enseignant'
    _inherit=['mail.thread', 'mail.activity.mixin',]

    name = fields.Char(
        string='Nom',
        compute='_compute_name',
        store=True,
    )

    description = fields.Text(
        string='Description',
    )

    # Enseignant lié à la programmation de cours
    employee_id = fields.Many2one(
        'hr.employee',
        string='Enseignant',
    )

    payment_ids = fields.One2many(
        'payment.debt',
        'debt_id',
        'Remboursements dette'
    )

    amount = fields.Float(
        'Montant',
        default=0.0,
    )

    rest_amount = fields.Float(
        string='Montant restant',
        compute='_compute_amount',
        store=True
    )

    @api.depends('payment_ids', 'amount')
    def _compute_amount(self):
        for record in self:
            amount = record.amount
            for payment_id in record.payment_ids:
                amount -= payment_id.amount
            if amount < 0.0:
                amount = 0.0
            record.rest_amount = amount

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

    @api.depends('employee_id', 'start_date', 'end_date')
    def _compute_name(self):
        for record in self:
            employee_name = record.employee_id.name if record.employee_id.id else ''
            start_date = datetime.strftime(record.start_date, DATE_FORMAT_FR) if record.start_date else ''
            end_date = datetime.strftime(record.end_date, DATE_FORMAT_FR) if record.end_date else ''
            name = '{} ({}-{})'.format(employee_name, start_date, end_date)
            while True:
                if name.find('()') != -1:
                    name = name.replace('()', '')
                else:
                    break
            while True:
                if name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            name = name.upper()
            record.name = name

    @api.constrains('start_date', 'end_date')
    def _constrains_date(self):
        for record in self:
            if record.start_date > record.end_date:
                raise ValidationError("La date de fin doit être supérieure ou égale à la date de début")

    @api.constrains('amount')
    def _constrains_amount(self):
        for record in self:
            if record.amount <= 0.0:
                raise ValidationError("Le montant doit être supérieur à 0")

class PaymentDebt(models.Model):
    _name = 'payment.debt'
    _description = 'Remboursement dette'
    _inherit=['mail.thread', 'mail.activity.mixin',]

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

    @api.depends('debt_id')
    def _compute_name(self):
        for record in self:
            record.name = record.debt_id.name

    @api.constrains('amount')
    def _constrains_amount(self):
        for record in self:
            if record.amount <= 0.0:
                raise ValidationError("Le montant doit être supérieur à 0")
