# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re


class siantou_emploidetemp_emploidetemp(models.Model):
    _name = 'siantou_emploidetemp.emploidetemp'
    _description = 'siantou_emploidetemp.emploidetemp'
    _sql_constraints = [('siantou_emploidetemp_emploidetemp_filiere_niveau_semestre_unique', 'unique(filiere_id, niveau_id, semestre_id)', "Les champs Filiere, Niveau, Semestre sont uniques pour chaque Emploi de temps.!")]

    filiere_id = fields.Many2one('siantou_emploidetemp.filiere', string='Filiere', required=True)
    niveau_id = fields.Many2one('siantou_emploidetemp.niveau', string='Niveau', required=True)
    semestre_id = fields.Many2one('siantou_emploidetemp.semestre', string='Semestre', required=True)

    @api.constrains('niveau', 'semestre')
    def _check_constrains(self):
        for record in self:
            if int(record.niveau.valeur) == 0 or int(record.semestre.valeur) == 0:
                raise ValidationError(f'Les champs niveau, semestre sont > 0')


class siantou_emploidetemp_programmationdecour(models.Model):
    _name = 'siantou_emploidetemp.programmationdecour'
    _description = 'siantou_emploidetemp.programmationdecour'
    _sql_constraints = [('siantou_emploidetemp_programmationdecour_emploidetemp_matiere_unique', 'unique(emploidetemp_id, matiere_id)', "Les champs Emploi de temps, Matiere sont uniques pour chaque Programmation de cours.!")]

    emploidetemp_id = fields.Many2one('siantou_emploidetemp.emploidetemp', string='Emploi de temps', required=True)
    matiere_id = fields.Many2one('siantou_emploidetemp.matiere', string='Matiere', required=True)
    debut = fields.Date(string='Heure debut', required=True, default=fields.Date.today())
    fin = fields.Date(string='Heure fin', required=True, default=fields.Date.today())
    configuration_id = fields.Many2one('siantou_emploidetemp.configuration', string='Configuration', required=True)

    @api.constrains('debut', 'fin')
    def _check_constrains(self):
        for record in self:
            if record.debut >= record.fin:
                raise ValidationError(f'Le champ Heure fin > Heure debut')


class siantou_emploidetemp_niveau(models.Model):
    _name = 'siantou_emploidetemp.niveau'
    _description = 'siantou_emploidetemp.niveau'
    _sql_constraints = [('siantou_emploidetemp_niveau_valeur_unique', 'unique(valeur)', "Le champ Niveau est unique pour chaque Niveau.!")]

    intitule = fields.Char(string='Intitule', required=True)
    valeur = fields.Selection(selection=[(f'{i}', f'{i}') for i in list(range(1, 9))], string='Niveau', required=True, default='1')


class siantou_emploidetemp_semestre(models.Model):
    _name = 'siantou_emploidetemp.semestre'
    _description = 'siantou_emploidetemp.semestre'
    _sql_constraints = [('siantou_emploidetemp_semestre_annee_valeur_unique', 'unique(annee, valeur)', "Les champs Annee scolaire, Semestre sont uniques pour chaque Semestre.!")]

    annee = fields.Char(string='Annee scolaire', required=True, default='2023-2024')
    valeur = fields.Selection(selection=[(f'{i}', f'{i}') for i in list(range(1, 3))], string='Semestre', required=True, default='1')
    debut = fields.Date(string='Date debut', required=True, default=fields.Date.today())
    fin = fields.Date(string='Date fin', required=True, default=fields.Date.today())
    matiere_ids = fields.Many2many('siantou_emploidetemp.matiere', 'siantou_emploidetemp_semestre_matiere', 'semestre_id', 'matiere_id', string='Matiere')

    def generator_page(self):
        return {
            'url': '/siantou_emploidetemp/semestre/%s' % (self.id),
            'type': 'ir.actions.act_url',
            'target': 'self'
        }

    @api.constrains('annee', 'debut', 'fin')
    def _check_constrains(self):
        for record in self:
            if (re.match(r'^[0-9]{4}-[0-9]{4}$', record.annee) is None) or (int(re.findall(r'^([0-9]{4})-([0-9]{4})$', record.annee)[0][0]) >= int(re.findall(r'^([0-9]{4})-([0-9]{4})$', record.annee)[0][1])):
                raise ValidationError(f'Le champ Annee scolaire a pour format ex. 2023-2024')
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
            if (re.match(r'^[0-9]+$', record.capacite) is None) or (int(record.capacite) < 1):
                raise ValidationError(f'Le champ Capacite est > 0')


class siantou_emploidetemp_filiere(models.Model):
    _name = 'siantou_emploidetemp.filiere'
    _description = 'siantou_emploidetemp.filiere'
    _sql_constraints = [('siantou_emploidetemp_filiere_code_niveau_id_unique', 'unique(code, niveau_id)', "Les champs Code, Niveau sont uniques pour chaque Filiere.!")]

    intitule = fields.Char(string='Intitule', required=True)
    code = fields.Char(string='Code', required=True)
    niveau_id = fields.Many2one('siantou_emploidetemp.niveau', string='Niveau', required=True)
    matiere_ids = fields.Many2many('siantou_emploidetemp.matiere', 'siantou_emploidetemp_filiere_matiere', 'filiere_id', 'matiere_id', string='Matiere')


class siantou_emploidetemp_matiere(models.Model):
    _name = 'siantou_emploidetemp.matiere'
    _description = 'siantou_emploidetemp.matiere'
    _sql_constraints = [('siantou_emploidetemp_matiere_code_niveau_id_unique', 'unique(code, niveau_id)', "Les champs Code, Niveau sont uniques pour chaque Matiere.!")]

    intitule = fields.Char(string='Intitule', required=True)
    code = fields.Char(string='Code', required=True)
    tronccommun = fields.Boolean(string='Tronc commun', required=True, default=False)
    quotahoraire = fields.Char(string='Quota horaire', required=True, default='0')
    niveau_id = fields.Many2one('siantou_emploidetemp.niveau', string='Niveau', required=True)
    filiere_ids = fields.Many2many('siantou_emploidetemp.filiere', 'siantou_emploidetemp_filiere_matiere', 'matiere_id', 'filiere_id', string='Filiere', required=True)
    semestre_ids = fields.Many2many('siantou_emploidetemp.semestre', 'siantou_emploidetemp_semestre_matiere', 'matiere_id', 'semestre_id', string='Semestre', required=True)

    @api.constrains('quotahoraire')
    def _check_constrains(self):
        for record in self:
            if (re.match(r'^[0-9]+$', record.quotahoraire) is None) or (int(record.quotahoraire) < 1):
                raise ValidationError(f'Le champ Quota horaire est > 0')


class siantou_emploidetemp_configuration(models.Model):
    _name = 'siantou_emploidetemp.configuration'
    _description = 'siantou_emploidetemp.configuration'
    _sql_constraints = [('siantou_emploidetemp_configuration_debut_fin_unique', 'unique(debut, fin)', "Les champs Heure debut, Heure fin sont uniques pour chaque Configuration.!")]

    intitule = fields.Char(string='Intitule', required=True)
    debut = fields.Char(string='Heure debut', required=True, default='12:30')
    fin = fields.Char(string='Heure fin', required=True, default='12:30')

    @api.constrains('debut', 'fin')
    def _check_constrains(self):
        for record in self:
            if (re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', record.debut) is None) or (re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', record.fin) is None):
                raise ValidationError(f'Les champs Heure debut, Heure fin ont pour format ex. 12:30')
            if record.debut >= record.fin:
                raise ValidationError(f'Le champ Heure fin > Heure debut')
