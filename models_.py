# -*- coding: utf-8 -*-

from odoo import models, fields, api


class siantou_emploiedetemps(models.Model):
    _name = 'siantou_emploiedetemps.siantou_emploiedetemps'
    _description = 'siantou_emploiedetemps.siantou_emploiedetemps'

    matiere_id = fields.Many2one('siantou.matiere', string='Matiere')
    filiere_id = fields.Many2one('siantou.filiere', string='Filiere')
    niveau = fields.Selection(selection=[('1' 'Niveau 1'), ('2' 'Niveau 2'), ('3' 'Niveau 3'), ('4' 'Niveau 4'), ('5' 'Niveau 5')], string='Niveau', default='1')
    jourdelasemaine = fields.Selection(selection=[('0' 'Lundi'), ('1' 'Mardi'), ('2' 'Mercredi'), ('3' 'Jeudi'), ('4' 'Vendredi'), ('5' 'Samedi'), ('6' 'Dimanche')], string='Jour de la semaine', default='0')
    heuredujour = fields.Selection(selection=[(f"{i}", f"{i}") for i in list(range(0, 24))], string='Heure du jour', default='0')
    minutedujour = fields.Selection(selection=[(f"{i}", f"{i}") for i in list(range(0, 60))], string='Minute du jour', default='0')
    datedujour = fields.Char(string='Date du jour', compute='_calcule_datedujour')

    @api.depends('heuredujour', 'minutedujour')
    def _calcule_datedujour(self):
        for record in self:
            record.datedujour = "{}:{}".format(record.heuredujour, record.minutedujour)
