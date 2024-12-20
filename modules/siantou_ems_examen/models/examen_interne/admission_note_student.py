# -*- coding: utf-8 -*-

from odoo import models, fields, api,tools, _
import logging
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger("++++++++++++++")

class RunNoteCandidat(models.Model):
    """
    Classe pour caluler la note des candidat
    """
    _name = "siantou.ems.admission.run.note"

    candidat_id = fields.Many2one('education.application', string='Candidat')

    nationalite_id = fields.Many2one('res.country', related='candidat_id.nationality', string='Nationalité')

    registre_id = fields.Many2one('siantou.session.registre')

    matricule = fields.Char('Matricule', required=True)

    moyenne = fields.Float('Moyenne', compute="_compute_moyenne")

    line_note_ids = fields.One2many('siantou.ems.admission.run.note.line', 'candidat_note_id')

    rang = fields.Integer('rang par paye',  compute='_compute_rang_contry')

    rang_all = fields.Integer('rang global',  compute='_compute_rang')
    
    state = fields.Selection([
        ('cancel', 'Éliminer'),
        ('not_cancel', 'Non Éliminer'),
    ], string='Statut', default='not_cancel')
    

    
    @api.depends('moyenne')
    def _compute_rang_contry(self):
        for rec in self:
            rec.rang = 0
            candidat_ids = self.search([("registre_id","=", rec.registre_id.id),("candidat_id.nationality","=", rec.candidat_id.nationality.id)])
            notes = candidat_ids.sorted(lambda r: r.moyenne,reverse=True)
            for pos in range(len(notes)):
                if notes[pos].id == rec.id:
                    rec.rang = pos+1

    @api.depends('moyenne')
    def _compute_rang(self):
        for rec in self:
            rec.rang_all = 0
            candidat_ids = self.search([("registre_id","=", rec.registre_id.id)])
            notes = candidat_ids.sorted(lambda r: r.moyenne,reverse=True)
            for pos in range(len(notes)):
                if notes[pos].id == rec.id:
                    rec.rang_all = pos+1
                
    
    
    @api.depends('line_note_ids.note')
    def _compute_moyenne(self):
        self.moyenne = 0
        note_some = 0 
        nbr_note = 0
        for rec in self:
            for line in rec.line_note_ids:
                if line.obligatory and line.note == 0:
                    rec.statut = "cancel"
                    break
                if line.note != 100:
                    nbr_note +=1 
                    note_some+=line.note

            rec.moyenne = (note_some / nbr_note)

class RunNoteCandidat(models.Model):
    """
    Liste des matieres et note par candidat 
    """
    _name = "siantou.ems.admission.run.note.line"


    matiere_id = fields.Many2one('education.subject', string='Matière')
    
    obligatory = fields.Boolean('Obligatoire',related='matiere_id.obligatory' ,default=False)

    note = fields.Float('note')

    candidat_note_id = fields.Many2one('siantou.ems.admission.run.note')


