# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class siantou_salledecour(models.Model):
    _name = 'siantou.salledecour'
    _description = 'siantou.salledecour'
    _sql_constraints = [('siantou_salledecour_code_unique', 'unique(code)', "Le champ code est unique pour chaque Salle de cours.!")]

    intitule = fields.Char(string='Intitule', required=True)
    code = fields.Char(string='Code', required=True)
    capacite = fields.Integer(string='Capacite', required=True)


class siantou_niveau(models.Model):
    _name = 'siantou.niveau'
    _description = 'siantou.niveau'
    _sql_constraints = [('siantou_niveau_valeur_unique', 'unique(valeur)', "Le champ valeur est unique pour chaque Niveau.!")]

    intitule = fields.Char(string='Intitule', required=True)
    valeur = fields.Selection(selection=[(f'{i}', f'{i}') for i in list(range(1, 9))], string='Valeur', required=True, default='1')


class siantou_semestre(models.Model):
    _name = 'siantou.semestre'
    _description = 'siantou.semestre'
    _sql_constraints = [('siantou_semestre_annee_valeur_unique', 'unique(annee, valeur)', "Les champs annee, valeur sont uniques pour chaque Semestre.!")]

    annee = fields.Integer(string='Annee', required=True)
    valeur = fields.Selection(selection=[(f'{i}', f'{i}') for i in list(range(1, 3))], string='Valeur', required=True, default='1')

    @api.constrains('annee')
    def _check_exist(self):
        for record in self:
            if len(str(record.annee)) != 4:
                raise ValidationError(f'Le champ annee contient 4 chiffres')


class siantou_emploidetemp(models.Model):
    _name = 'siantou.emploidetemp'
    _description = 'siantou.emploidetemp'
    _sql_constraints = [('siantou_emploidetemp_filiere_niveau_semestre_unique', 'unique(filiere, niveau, semestre)', "Les champs filiere, niveau, semestre sont uniques pour chaque Emploi de temps.!")]

    filiere = fields.Many2one('siantou.filiere', string='Filiere', required=True)
    niveau = fields.Many2one('siantou.niveau', string='Niveau', required=True)
    semestre = fields.Many2one('siantou.semestre', string='Semestre', required=True)

    @api.constrains('niveau', 'semestre')
    def _check_exist(self):
        for record in self:
            if int(record.niveau.valeur) == 0 or int(record.semestre.valeur) == 0:
                raise ValidationError(f'Les champs niveau, semestre sont > 0')


class siantou_programmationdecour(models.Model):
    _name = 'siantou.programmationdecour'
    _description = 'siantou.programmationdecour'
    _sql_constraints = [('siantou_programmationdecour_emploidetemp_matiere_unique', 'unique(emploidetemp, matiere)', "Les champs emploidetemp, matiere sont uniques pour chaque Programmation de cours.!")]

    emploidetemp = fields.Many2one('siantou.emploidetemp', string='Emploi de temps', required=True)
    matiere = fields.Many2one('siantou.matiere', string='Matiere', required=True)
