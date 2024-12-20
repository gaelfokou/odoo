# -*- coding: utf-8 -*-

from odoo import models, fields, api,tools, _
import logging
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger("++++++++++++++")

class ExamenPlannifier(models.Model):
    _name = 'siantou.ems.examen.plannifier'
    _description = "Model pour gerer les plannification des examens"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    
    name = fields.Char('code')

    classe_id = fields.Many2one('education.class.division', string='Classe', required=True, tracking=True,states={
        'draft': [('readonly', False)]})

    semestre_id = fields.Many2one('education.semestre', string='Semestre', required=True,tracking=True,states={
        'draft': [('readonly', False)]})

    date = fields.Date('Date', required=True, tracking=True,states={
        'draft': [('readonly', False)]})

    annee_academique_id = fields.Many2one('education.academic.year', string='Année académique', domain=[('active','=',True)], required=True)

    line_examen_ids = fields.One2many('siantou.ems.examen.plannifier.line', 'examen_id', string="Line d'examen",states={
        'draft': [('readonly', False)]})

    registre_examen_ids = fields.One2many('siantou.ems.examen.registre', 'examen_plannifier_id','Régistre')


    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validated', 'Valider'),
        ('confirm', 'Confirmer'),
        ('cancel', 'Annuler'),
        ('modify', 'Modifier'),
        ('done', 'Fait'),
    ], string='state', 
    default='draft'
    )

    # @api.onchange('semestre_id','classe_id')
    # def _onchange_matiere(self):
    #     for rec in self:
    #         if rec.classe_id and rec.semestre_id:
    #             _logger.info("ok")
    #             syllabus_ids = self.env['education.syllabus'].search([('unite_enseignement_id.semestre_id','=',rec.semestre_id.id),('class_id','=',rec.classe_id.class_id.id)])
    #             if len(rec.line_examen_ids) > 0:
    #                 for elt in rec.line_examen_ids:
    #                     elt.unlink()
    #             for line in syllabus_ids:
    #                 rec.line_examen_ids = [
    #                     (
    #                         0,
    #                         0,
    #                         {
    #                             "matiere_id": line.subject_id,
    #                             "coeficien": line.coefficient,
    #                             "pourcentage_cc": line.pourcentage_cc,
    #                             "unite_enseignement_id" : line.unite_enseignement_id,
    #                             "pourcentage_exam": line.pourcentage_exam,
    #                             "pourcentage_presence": line.pourcentage_presence
    #                         },
    #                     )
    #                 ]

    
    @api.onchange('semestre_id', 'classe_id')
    def _onchange_matiere(self):
        for rec in self:
            if rec.classe_id and rec.semestre_id:
                syllabus_ids = self.env['education.syllabus'].search([('unite_enseignement_id.semestre_id','=',rec.semestre_id.id),('class_id','=',rec.classe_id.class_id.id)])
                if len(rec.line_examen_ids) > 0:
                    for elt in rec.line_examen_ids:
                        elt.unlink()
                for line in syllabus_ids:
                    rec.line_examen_ids = [
                        (
                            0,
                            0,
                            {
                                "matiere_id": line.subject_id,
                                "coeficien": line.under_subject_credit,
                                "pourcentage_cc": line.pourcentage_cc,
                                "unite_enseignement_id" : line.unite_enseignement_id,
                                "pourcentage_exam": line.pourcentage_exam,
                                "pourcentage_presence": line.pourcentage_presence
                            },
                        )
                    ]
    
    def action_validate(self):
        for rec in self:
            num = self.env["ir.sequence"].next_by_code("aft_examen.identifiant")
            rec.name = num
            rec.state = 'validated'
            if rec.state == "validated":
                return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': 'success',
                            'message': "Planification validée avec succès !",
                            'next': {'type': 'ir.actions.act_window_close'},
                        }
                    }
    
    def action_confirm(self):
        registre_obj = self.env['siantou.ems.examen.registre']
        for rec in self:
            syllabus_ids = self.env['education.syllabus'].search([('unite_enseignement_id.semestre_id','=',rec.semestre_id.id),('class_id','=',rec.classe_id.class_id.id)])
            for line in syllabus_ids:
                registre_obj.create({
                    "matiere_id" : line.subject_id.id,
                    "class_id" : rec.classe_id.id,
                    "semestre_id" : rec.semestre_id.id,
                    "annee_academique_id" : rec.annee_academique_id.id,
                    "coeficien": line.under_subject_credit,
                    "pourcentage_cc": line.pourcentage_cc,
                    "pourcentage_exam": line.pourcentage_exam,
                    "pourcentage_presence": line.pourcentage_presence,
                    "unite_enseignement_id" : line.unite_enseignement_id.id,
                    "examen_plannifier_id" : rec.id
                })
            rec.state = 'confirm'
            if rec.state == "confirm":
                return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'type': 'success',
                                'message': "Planification confirmée avec succès !",
                                'next': {'type': 'ir.actions.act_window_close'},
                            }
                        }
            
    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'
            if rec.state == "cancel":
                return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'type': 'success',
                                'message': "Planification annulée avec succès !",
                                'next': {'type': 'ir.actions.act_window_close'},
                            }
                        }

    def action_modifier(self):
        for rec in self:
            rec.state = 'draft'

    def action_calcul(self):
        studen_ids = self.env["oe.school.student"].search([('class_id', '=', self.classe_id.id)], offset=0, limit=None, order=None, count=False)
        studen_obj = self.env["siantou.ems.examen.student"]
        for rec in self:
            for line in rec.registre_examen_ids:
                if line.state != "confirm":
                    raise ValidationError("Veuillez confirmer les U.E")
                for emp in line.examen_registre_participant_ids:
                    if emp.state != "confirm":
                        raise ValidationError("Veuillez confirmer les notes introduitent !")
            for emp in studen_ids:
                stud = studen_obj.create({
                    "student_id" : emp.id,
                    "semestre_id" : rec.semestre_id.id,
                    "class_id" : rec.classe_id.id,
                    "anne_academique_id" : rec.annee_academique_id.id,
                    "examen_planifier_id" : rec.id
                })
            
                stud.action_confirm()
            rec.state = 'done'
            if rec.state == "done":
                return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'type': 'success',
                                'message': "Calcul terminée avec succès !",
                                'next': {'type': 'ir.actions.act_window_close'},
                            }
                        }



class ExamenLine(models.Model):
    _name = 'siantou.ems.examen.plannifier.line'
    _description = "Model pour gerer les lignes d'examen"

    matiere_id = fields.Many2one('education.subject', string='Matière', required=True)

    # coeficien = fields.Float('Coéficient', required=True)
    
    coeficien = fields.Float('Crédit', required=True)
    
    pourcentage_cc = fields.Integer('Pourcentage CC',default=30,)
    
    pourcentage_exam = fields.Integer('Pourcentage Examen', default=50)

    pourcentage_presence = fields.Integer('Pourcentage de présence', default=20)

    unite_enseignement_id = fields.Many2one('education.unite.enseignement', string="Unité d'enseignement")

    examen_id = fields.Many2one('siantou.ems.examen.plannifier')

    