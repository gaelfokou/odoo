# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


class siantou_emploidetemp_emploidetemp(models.Model):
    _name = 'siantou_emploidetemp.emploidetemp'
    _description = 'siantou_emploidetemp.emploidetemp'
    _sql_constraints = [('siantou_emploidetemp_emploidetemp_filiere_id_niveau_id_semestre_id_salledecour_id_matiere_id_configuration_id_unique', 'unique(filiere_id, niveau_id, semestre_id, salledecour_id, matiere_id, configuration_id)', "Les champs Filiere, Niveau, Semestre, Salle de cours, Matiere, Configuration sont uniques pour chaque Emploi de temps.!")]

    filiere_id = fields.Many2one('siantou_emploidetemp.filiere', string='Filiere', required=True)
    niveau_id = fields.Many2one('siantou_emploidetemp.niveau', string='Niveau', required=True)
    semestre_id = fields.Many2one('siantou_emploidetemp.semestre', string='Semestre', required=True)
    salledecour_id = fields.Many2one('siantou_emploidetemp.salledecour', string='Salle de cours', required=True)
    matiere_id = fields.Many2one('siantou_emploidetemp.matiere', string='Matiere', required=False, default=None)
    configuration_id = fields.Many2one('siantou_emploidetemp.configuration', string='Configuration', required=False, default=None)
    intitule = fields.Char(string='Intitule', compute='_compute_intitule', store=True, default=None)
    debut = fields.Datetime(string='Heure debut', required=True, default=fields.Datetime.now())
    fin = fields.Datetime(string='Heure fin', required=True, default=fields.Datetime.now())

    @api.constrains('niveau_id', 'semestre_id', 'debut', 'fin')
    def _check_constrains(self):
        for record in self:
            if (((not record.matiere_id.id) and (not record.configuration_id.id)) or ((record.matiere_id.id) and (record.configuration_id.id))):
                raise ValidationError(f'Le champ Matiere != Configuration')
            if record.debut and record.fin:
                if record.debut >= record.fin:
                    raise ValidationError(f'Le champ Heure fin > Heure debut')

    @api.depends('matiere_id', 'configuration_id')
    def _compute_intitule(self):
        try:
            _logger.info(f'----------- tototototototo 1 Your information log message {DATETIME_FORMAT} -----------')
            _logger.warning(f'----------- tototototototo 1 Your warning log message {DATETIME_FORMAT} -----------')
            _logger.error(f'----------- tototototototo 1 Your error log message {DATETIME_FORMAT} -----------')
        except Exception as e:
            _logger.exception(f'----------- tototototototo 1 An error occurred : {e} -----------')
        for record in self:
            if (((not record.matiere_id.id) and (record.configuration_id.id)) or ((record.matiere_id.id) and (not record.configuration_id.id))):
                if record.matiere_id.id:
                    record.intitule = record.matiere_id.intitule
                if record.configuration_id.id:
                    record.intitule = record.configuration_id.intitule

    @api.onchange('matiere_id', 'debut', 'fin')
    def _check_onchange(self):
        try:
            _logger.info(f'----------- tototototototo 2 Your information log message {DATETIME_FORMAT} -----------')
            _logger.warning(f'----------- tototototototo 2 Your warning log message {DATETIME_FORMAT} -----------')
            _logger.error(f'----------- tototototototo 2 Your error log message {DATETIME_FORMAT} -----------')
        except Exception as e:
            _logger.exception(f'----------- tototototototo 2 An error occurred : {e} -----------')
        for record in self:
            if (((not record.matiere_id.id) and (record.configuration_id.id)) or ((record.matiere_id.id) and (not record.configuration_id.id))):
                if record.matiere_id.id:
                    record.configuration_id = None
                    record.intitule = record.matiere_id.intitule
                    date_debut = datetime.strptime(record.debut, DATETIME_FORMAT)
                    record.fin = date_debut + timedelta(days=1, hours=1, minutes=30)

    @api.onchange('configuration_id')
    def _check_onchange(self):
        for record in self:
            if (((not record.matiere_id.id) and (record.configuration_id.id)) or ((record.matiere_id.id) and (not record.configuration_id.id))):
                if record.configuration_id.id:
                    record.matiere_id = None
                    record.intitule = record.configuration_id.intitule


class siantou_emploidetemp_niveau(models.Model):
    _name = 'siantou_emploidetemp.niveau'
    _description = 'siantou_emploidetemp.niveau'
    _sql_constraints = [('siantou_emploidetemp_niveau_valeur_unique', 'unique(valeur)', "Le champ Valeur est unique pour chaque Niveau.!")]

    intitule = fields.Char(string='Intitule', required=True)
    valeur = fields.Selection(selection=[(f'{i}', f'{i}') for i in list(range(1, 9))], string='Valeur', required=True, default='1')


class siantou_emploidetemp_semestre(models.Model):
    _name = 'siantou_emploidetemp.semestre'
    _description = 'siantou_emploidetemp.semestre'
    _sql_constraints = [('siantou_emploidetemp_semestre_annee_valeur_unique', 'unique(annee, valeur)', "Les champs Annee scolaire, Valeur sont uniques pour chaque Semestre.!")]

    annee = fields.Char(string='Annee scolaire', required=True, default='2023-2024')
    valeur = fields.Selection(selection=[(f'{i}', f'{i}') for i in list(range(1, 3))], string='Valeur', required=True, default='1')
    debut = fields.Date(string='Date debut', required=True, default=fields.Date.today())
    fin = fields.Date(string='Date fin', required=True, default=fields.Date.today())
    matiere_ids = fields.Many2many('siantou_emploidetemp.matiere', 'siantou_emploidetemp_semestre_matiere', 'semestre_id', 'matiere_id', string='Matiere', required=True)

    def generator_page(self):
        return {
            'url': '/siantou_emploidetemp/semestre/%s' % (self.id),
            'type': 'ir.actions.act_url',
            'target': 'self'
        }

    @api.constrains('annee', 'debut', 'fin')
    def _check_constrains(self):
        for record in self:
            if record.annee:
                if (re.match(r'^[0-9]{4}-[0-9]{4}$', record.annee) is None) or (int(re.findall(r'^([0-9]{4})-([0-9]{4})$', record.annee)[0][0]) >= int(re.findall(r'^([0-9]{4})-([0-9]{4})$', record.annee)[0][1])):
                    raise ValidationError(f'Le champ Annee scolaire a pour format ex. 2023-2024')
            if record.debut and record.fin:
                if record.debut >= record.fin:
                    raise ValidationError(f'Le champ Date fin > Date debut')


class siantou_emploidetemp_salledecour(models.Model):
    _name = 'siantou_emploidetemp.salledecour'
    _description = 'siantou_emploidetemp.salledecour'
    _sql_constraints = [('siantou_emploidetemp_salledecour_code_unique', 'unique(code)', "Le champ Code est unique pour chaque Salle de cours.!")]

    intitule = fields.Char(string='Intitule', required=True)
    code = fields.Char(string='Code', required=True)
    capacite = fields.Char(string='Capacite', required=True, default='0')

    @api.constrains('capacite')
    def _check_constrains(self):
        for record in self:
            if record.capacite:
                if (re.match(r'^[0-9]+$', record.capacite) is None) or (int(record.capacite) < 1):
                    raise ValidationError(f'Le champ Capacite est > 0')


class siantou_emploidetemp_filiere(models.Model):
    _name = 'siantou_emploidetemp.filiere'
    _description = 'siantou_emploidetemp.filiere'
    _inherits = {'siantou_emploidetemp.niveau': 'niveau_id'}
    _sql_constraints = [('siantou_emploidetemp_filiere_code_niveau_id_unique', 'unique(code, niveau_id)', "Les champs Code, Niveau sont uniques pour chaque Filiere.!")]

    intitule = fields.Char(string='Intitule', required=True)
    code = fields.Char(string='Code', required=True)
    niveau_id = fields.Many2one('siantou_emploidetemp.niveau', string='Niveau', required=True)
    matiere_ids = fields.Many2many('siantou_emploidetemp.matiere', 'siantou_emploidetemp_filiere_matiere', 'filiere_id', 'matiere_id', string='Matiere', required=True)


class siantou_emploidetemp_matiere(models.Model):
    _name = 'siantou_emploidetemp.matiere'
    _description = 'siantou_emploidetemp.matiere'
    _sql_constraints = [('siantou_emploidetemp_matiere_code_niveau_id_unique', 'unique(code, niveau_id)', "Les champs Code, Niveau sont uniques pour chaque Matiere.!")]

    intitule = fields.Char(string='Intitule', required=True)
    code = fields.Char(string='Code', required=True)
    tronccommun = fields.Boolean(string='Tronc commun', required=True, default=False)
    jour = fields.Boolean(string='Jour', required=True, default=True)
    nuit = fields.Boolean(string='Nuit', required=True, default=False)
    quotahoraire = fields.Char(string='Quota horaire', required=True, default='0')
    niveau_id = fields.Many2one('siantou_emploidetemp.niveau', string='Niveau', required=True)
    filiere_ids = fields.Many2many('siantou_emploidetemp.filiere', 'siantou_emploidetemp_filiere_matiere', 'matiere_id', 'filiere_id', string='Filiere', required=True)
    semestre_ids = fields.Many2many('siantou_emploidetemp.semestre', 'siantou_emploidetemp_semestre_matiere', 'matiere_id', 'semestre_id', string='Semestre', required=True)

    @api.constrains('quotahoraire')
    def _check_constrains(self):
        for record in self:
            if record.quotahoraire:
                if (re.match(r'^[0-9]+$', record.quotahoraire) is None) or (int(record.quotahoraire) < 1):
                    raise ValidationError(f'Le champ Quota horaire est > 0')


class siantou_emploidetemp_configuration(models.Model):
    _name = 'siantou_emploidetemp.configuration'
    _description = 'siantou_emploidetemp.configuration'
    _sql_constraints = [('siantou_emploidetemp_configuration_code_unique', 'unique(code)', "Le champ Code est unique pour chaque Configuration.!")]

    intitule = fields.Char(string='Intitule', required=True)
    code = fields.Char(string='Code', required=True)
    debut = fields.Char(string='Heure debut', required=False, default='12:30')
    fin = fields.Char(string='Heure fin', required=False, default='12:30')
    jour = fields.Selection(selection=[('7', 'Tous les jours'), ('0', 'Lundi'), ('1', 'Mardi'), ('2', 'Mercredi'), ('3', 'Jeudi'), ('4', 'Vendredi'), ('5', 'Samedi'), ('6', 'Dimanche')], string='Jour', required=True, default='7')
    date = fields.Date(string='Date', required=False, default=None)

    @api.constrains('debut', 'fin')
    def _check_constrains(self):
        for record in self:
            if record.debut and record.fin:
                if (re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', record.debut) is None) or (re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', record.fin) is None):
                    raise ValidationError(f'Les champs Heure debut, Heure fin ont pour format ex. 12:30')
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
