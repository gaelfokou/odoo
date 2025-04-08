# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import logging
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
from pytz import timezone
import pytz

_logger = logging.getLogger(__name__)

TIME_FORMAT = '%H:%M'
DATE_FORMAT = '%Y-%m-%d'
DATE_FORMAT_FR = '%d-%m-%Y'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATETIME_FORMAT_FR = '%d-%m-%Y %H:%M:%S'


class siantou_emploidutemp_emploidutemp_model(models.Model):
    _name = 'siantou_emploidutemp.emploidutemp'
    _description = 'siantou_emploidutemp.emploidutemp'
    _sql_constraints = [('siantou_emploidutemp_emploidutemp_filiere_id_niveau_id_semestre_id_salledecour_id_matiere_id_configuration_id_unique', 'unique(filiere_id, niveau_id, semestre_id, salledecour_id, matiere_id, configuration_id)', "Les champs Filiere, Niveau, Semestre, Salle de cours, Matiere, Configuration sont uniques pour chaque Emploi du temps.!")]

    filiere_id = fields.Many2one('siantou_emploidutemp.filiere', string='Filiere')
    niveau_id = fields.Many2one('siantou_emploidutemp.niveau', string='Niveau')
    semestre_id = fields.Many2one('siantou_emploidutemp.semestre', string='Semestre')
    salledecour_id = fields.Many2one('siantou_emploidutemp.salledecour', string='Salle de cours')
    matiere_id = fields.Many2one('siantou_emploidutemp.matiere', string='Matiere')
    configuration_id = fields.Many2one('siantou_emploidutemp.configuration', string='Configuration')
    name = fields.Char(string='Intitule', compute='_compute_name', store=True)
    date = fields.Date(string='Date')
    debut = fields.Char(string='Heure debut')
    fin = fields.Char(string='Heure fin')

    @api.constrains('debut', 'fin')
    def _check_constrains(self):
        for record in self:
            if record.debut and record.fin:
                if (re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', record.debut) is None) or (re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', record.fin) is None):
                    raise ValidationError(f'Les champs Heure debut, Heure fin ont pour format ex. {datetime.strftime(fields.Datetime.now(), TIME_FORMAT)}')
                if record.debut >= record.fin:
                    raise ValidationError(f'Le champ Heure fin > Heure debut')

    @api.constrains('niveau_id', 'semestre_id')
    def _check_constrains(self):
        for record in self:
            if ((not record.matiere_id.id and not record.configuration_id.id) or (record.matiere_id.id and record.configuration_id.id)):
                raise ValidationError(f'Le champ Matiere != Configuration')

    @api.onchange('matiere_id')
    def _check_onchange(self):
        for record in self:
            if ((not record.matiere_id.id and record.configuration_id.id) or (record.matiere_id.id and not record.configuration_id.id)):
                if record.matiere_id.id:
                    record.configuration_id = None
                    record.name = record.matiere_id.name

    @api.onchange('configuration_id')
    def _check_onchange(self):
        for record in self:
            if ((not record.matiere_id.id and record.configuration_id.id) or (record.matiere_id.id and not record.configuration_id.id)):
                if record.configuration_id.id:
                    record.matiere_id = None
                    record.name = record.configuration_id.name

    @api.depends('matiere_id', 'configuration_id')
    def _compute_name(self):
        for record in self:
            if ((not record.matiere_id.id and record.configuration_id.id) or (record.matiere_id.id and not record.configuration_id.id)):
                if record.matiere_id.id:
                    record.name = record.matiere_id.name
                if record.configuration_id.id:
                    record.name = record.configuration_id.name


class siantou_emploidutemp_niveau_model(models.Model):
    _name = 'siantou_emploidutemp.niveau'
    _description = 'siantou_emploidutemp.niveau'
    _sql_constraints = [('siantou_emploidutemp_niveau_valeur_unique', 'unique(valeur)', "Le champ Valeur est unique pour chaque Niveau.!")]

    name = fields.Char(string='Intitule')
    valeur = fields.Selection(selection=[(f'{i}', f'{i}') for i in list(range(1, 9))], string='Valeur', default='1')


class siantou_emploidutemp_semestre_model(models.Model):
    _name = 'siantou_emploidutemp.semestre'
    _description = 'siantou_emploidutemp.semestre'
    _sql_constraints = [('siantou_emploidutemp_semestre_annee_valeur_unique', 'unique(annee, valeur)', "Les champs Annee scolaire, Valeur sont uniques pour chaque Semestre.!")]

    name = fields.Char(string='Semestre')
    annee = fields.Char(string='Annee scolaire')
    valeur = fields.Selection(selection=[(f'{i}', f'{i}') for i in list(range(1, 3))], string='Valeur', default='1')
    debut = fields.Date(string='Date debut')
    fin = fields.Date(string='Date fin')
    matiere_ids = fields.Many2many('siantou_emploidutemp.matiere', 'siantou_emploidutemp_semestre_matiere', 'semestre_id', 'matiere_id', string='Matiere')

    @api.constrains('annee')
    def _check_constrains(self):
        for record in self:
            if record.annee:
                if (re.match(r'^[0-9]{4}-[0-9]{4}$', record.annee) is None) or (int(re.findall(r'^([0-9]{4})-([0-9]{4})$', record.annee)[0][0]) >= int(re.findall(r'^([0-9]{4})-([0-9]{4})$', record.annee)[0][1])):
                    raise ValidationError(f'Le champ Annee scolaire a pour format ex. {fields.Date.today().year}-{fields.Date.today().year+1}')

    @api.constrains('debut', 'fin')
    def _check_constrains(self):
        for record in self:
            if record.debut and record.fin:
                if record.debut >= record.fin:
                    raise ValidationError(f'Le champ Date fin > Date debut')

    def generator_page(self):
        return {
            'name': 'Générer un emploi du temps',
            'type': 'ir.actions.act_url',
            'url': '/siantou_emploidutemp/semestre/%s' % (self.id),
            'target': 'self'
        }

    def scanner_document(self):
        return {
            'name': 'Document scanner',
            'type': 'ir.actions.client',
            'tag': 'siantou_emploidutemp.document_scanner'
        }


class siantou_emploidutemp_salledecour_model(models.Model):
    _name = 'siantou_emploidutemp.salledecour'
    _description = 'siantou_emploidutemp.salledecour'
    _sql_constraints = [('siantou_emploidutemp_salledecour_code_unique', 'unique(code)', "Le champ Code est unique pour chaque Salle de cours.!")]

    name = fields.Char(string='Intitule')
    code = fields.Char(string='Code')
    capacite = fields.Char(string='Capacite', default='0')

    @api.constrains('capacite')
    def _check_constrains(self):
        for record in self:
            if record.capacite:
                if (re.match(r'^[0-9]+$', record.capacite) is None) or (int(record.capacite) < 1):
                    raise ValidationError(f'Le champ Capacite est > 0')


class siantou_emploidutemp_filiere_model(models.Model):
    _name = 'siantou_emploidutemp.filiere'
    _description = 'siantou_emploidutemp.filiere'
    _inherits = {'siantou_emploidutemp.niveau': 'niveau_id'}
    _sql_constraints = [('siantou_emploidutemp_filiere_code_niveau_id_unique', 'unique(code, niveau_id)', "Les champs Code, Niveau sont uniques pour chaque Filiere.!")]

    name = fields.Char(string='Intitule')
    code = fields.Char(string='Code')
    niveau_id = fields.Many2one('siantou_emploidutemp.niveau', string='Niveau')
    matiere_ids = fields.Many2many('siantou_emploidutemp.matiere', 'siantou_emploidutemp_filiere_matiere', 'filiere_id', 'matiere_id', string='Matiere')


class siantou_emploidutemp_matiere_model(models.Model):
    _name = 'siantou_emploidutemp.matiere'
    _description = 'siantou_emploidutemp.matiere'
    _sql_constraints = [('siantou_emploidutemp_matiere_code_niveau_id_unique', 'unique(code, niveau_id)', "Les champs Code, Niveau sont uniques pour chaque Matiere.!")]

    name = fields.Char(string='Intitule')
    code = fields.Char(string='Code')
    tronccommun = fields.Boolean(string='Tronc commun', default=False)
    jour = fields.Boolean(string='Jour', default=True)
    nuit = fields.Boolean(string='Nuit', default=False)
    quotahoraire = fields.Char(string='Quota horaire', default='0')
    niveau_id = fields.Many2one('siantou_emploidutemp.niveau', string='Niveau')
    filiere_ids = fields.Many2many('siantou_emploidutemp.filiere', 'siantou_emploidutemp_filiere_matiere', 'matiere_id', 'filiere_id', string='Filiere')
    semestre_ids = fields.Many2many('siantou_emploidutemp.semestre', 'siantou_emploidutemp_semestre_matiere', 'matiere_id', 'semestre_id', string='Semestre')

    @api.constrains('quotahoraire')
    def _check_constrains(self):
        for record in self:
            if record.quotahoraire:
                if (re.match(r'^[0-9]+$', record.quotahoraire) is None) or (int(record.quotahoraire) < 1):
                    raise ValidationError(f'Le champ Quota horaire est > 0')


class siantou_emploidutemp_configuration_model(models.Model):
    _name = 'siantou_emploidutemp.configuration'
    _description = 'siantou_emploidutemp.configuration'
    _sql_constraints = [('siantou_emploidutemp_configuration_code_unique', 'unique(code)', "Le champ Code est unique pour chaque Configuration.!")]

    name = fields.Char(string='Intitule')
    code = fields.Char(string='Code')
    date = fields.Date(string='Date')
    debut = fields.Char(string='Heure debut')
    fin = fields.Char(string='Heure fin')
    jour = fields.Selection(selection=[('7', 'Tous les jours'), ('0', 'Lundi'), ('1', 'Mardi'), ('2', 'Mercredi'), ('3', 'Jeudi'), ('4', 'Vendredi'), ('5', 'Samedi'), ('6', 'Dimanche')], string='Jour', default='7')

    @api.constrains('debut', 'fin')
    def _check_constrains(self):
        for record in self:
            if record.debut and record.fin:
                if (re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', record.debut) is None) or (re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', record.fin) is None):
                    raise ValidationError(f'Les champs Heure debut, Heure fin ont pour format ex. {datetime.strftime(fields.Datetime.now(), TIME_FORMAT)}')
                if record.debut >= record.fin:
                    raise ValidationError(f'Le champ Heure fin > Heure debut')

    @api.onchange('jour')
    def _check_onchange(self):
        for record in self:
            if ((record.jour) and (record.date)):
                if record.jour:
                    record.date = None

    @api.onchange('date')
    def _check_onchange(self):
        for record in self:
            if ((record.jour) and (record.date)):
                if record.date:
                    record.jour = '7'
