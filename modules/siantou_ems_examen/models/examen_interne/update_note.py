# -*- coding: utf-8 -*-

from odoo import models, fields, api,tools, _
import logging
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class ExamenPlannifier(models.Model):
    """
    Modèle pour modifier les notes des examen
    """
    _name = 'siantou.ems.examen.update.note'
    _description = "Modèle pour modifier les notes des examen"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char('code')

    semestre_id = fields.Many2one("education.semestre", string='Semestre', required=True,tracking=True)

    year_id = fields.Many2one('education.academic.year', string='Année académique',required=True,tracking=True)

    class_id = fields.Many2one("education.class.division", string='Classe', required=True,tracking=True)

    student_id = fields.Many2one("oe.school.student", string='Étudiant', required=True,tracking=True)

    type_examen_id = fields.Many2one("siantou.ems.type.examen", string="Type d'examen", required=True,tracking=True)

    subject_id = fields.Many2one("education.subject", string='Matière')

    note = fields.Float('Nouvelle note',required=True,tracking=True)

    motif_modification_note = fields.Char(
        string='Motif de la modification  de la note',
    )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validate', 'Valider'),
        ('confirm', 'Confirmer'),
        ('cancel', 'Annuler'),
    ], string='state', 
    default='draft'
    )

    @api.onchange('class_id')
    def _onchange_student(self):
        """
        Fonction pour charger les étudiants d'un class
        """
        for rec in self:
            if rec.class_id:
                student_id = self.env['oe.school.student'].search([('class_id','=',rec.class_id.id)], offset=0, limit=None, order=None, count=False)
                if student_id:
                    for emp in student_id:
                        rec.student_id = emp.id

    def action_validate(self):
        """
        Fonction pour valider une action
        """
        for rec in self:
            num = self.env["ir.sequence"].next_by_code("aft_examen.update")
            rec.name = num
            rec.state = 'validate'
            if rec.state == "validate":
                return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'type': 'success',
                                'message': "Validé avec succès !",
                                'next': {'type': 'ir.actions.act_window_close'},
                            }
                        }
    def action_confirm(self):
        """
        Fonction pour Confirmer une action
        """
        for rec in self:
            resultat_student = self.env["siantou.ems.examen.student"].search([
            ("anne_academique_id","=",rec.year_id.id),
            ("semestre_id","=",rec.semestre_id.id),
            ("class_id","=",rec.class_id.id),
            ])
            for std in resultat_student:
                    if std.student_id.id == rec.student_id.id:
                        for mat in std.examen_student_line_ids.examen_student_subject_line_ids:
                            if rec.subject_id.id == mat.matiere_id.id:
                                for note in mat.examen_student_subject_ids:
                                    if note.type_examen_id.id == rec.type_examen_id.id:
                                        note.note = rec.note
                            mat._compute_moyenne_matiere()
                            mat.examen_student_line_id._compute_moyenne()
                            mat.examen_student_line_id._compute_credit()
                            mat.examen_student_line_id.examen_student_id._compute_moyenne()
                            mat.examen_student_line_id.examen_student_id._compute_rang()
            rec.state = 'confirm'
            if rec.state == "confirm":
                return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'type': 'success',
                                'message': "Confirmé avec succès !",
                                'next': {'type': 'ir.actions.act_window_close'},
                            }
                        }

    def action_cancel(self):
        """
        Fonction pour valider une action
        """
        for rec in self:
            rec.state = 'cancel'
            if rec.state == "cancel":
                return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'type': 'success',
                                'message': "Annulé avec succès !",
                                'next': {'type': 'ir.actions.act_window_close'},
                            }
                        }
