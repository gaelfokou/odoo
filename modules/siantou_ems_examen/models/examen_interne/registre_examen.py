# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
from odoo.exceptions import UserError, ValidationError
_logger = logging.getLogger(" ")

class ExamenRegistre(models.Model):
    _name = 'siantou.ems.examen.registre'
    _description = "Model pour gerer les registre d'examen"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char('code')

    matiere_id = fields.Many2one('education.subject', string='Matiere', required=True, tracking=True)

    unite_enseignement_id = fields.Many2one('education.unite.enseignement', string='Unité d\'enseignement', required=True, tracking=True)

    class_id = fields.Many2one('education.class.division', string='Classe', required=True, tracking=True)

    semestre_id = fields.Many2one('education.semestre', string='Semestre', required=True, tracking=True)

    annee_academique_id = fields.Many2one('education.academic.year', string='Année académique',  tracking=True)

    coeficien = fields.Float('Credit', required=True)

    pourcentage_cc = fields.Integer('Pourcentage CC')

    pourcentage_exam = fields.Integer('Pourcentage Examen')

    pourcentage_presence = fields.Integer('Pourcentage de présence')

    examen_plannifier_id = fields.Many2one('siantou.ems.examen.plannifier', string='Plannification')

    examen_registre_participant_ids = fields.One2many('siantou.ems.examen.registre.line', 'examen_registre_id')

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validated', 'Valider'),
        ('confirm', 'Confirmer'),
    ], string='state', 
    default='draft'
    )

    @api.depends('class_id')
    def action_validate(self):
        number = 0

        type_examen_cc = self.env['siantou.ems.type.examen'].search([("code","=","CC")])
        type_examen_ef = self.env['siantou.ems.type.examen'].search([("code","=","SN")])
        type_examen_pr = self.env['siantou.ems.type.examen'].search([("code","=","PR")])
        for rec in self:
            if rec.class_id:
                num = self.env["ir.sequence"].next_by_code("aft_examen.create_register")
                rec.name = num
                students = self.env['oe.school.student'].search([('class_id','=',rec.class_id.id)])
                if len(rec.examen_registre_participant_ids) > 0:
                    for elt in rec.examen_registre_participant_ids:
                        elt.unlink()
                for line in students:
                    number +=1
                if rec.pourcentage_exam > 0:
                    rec.examen_registre_participant_ids = [
                            (0,0,
                                { 
                                    "type_examen_id" :  type_examen_cc.id,
                                    "number": number,
                                    "matiere_id" : rec.matiere_id.id,
                                    "Pourcentage" : rec.pourcentage_cc,
                                    "unite_enseignement_id" : rec.unite_enseignement_id.id,
                                    "coeficien" : rec.coeficien,
                                    "class_id" : rec.class_id.id,
                                    "anne_academique_id" : rec.annee_academique_id.id,
                                    "semestre_id" : rec.semestre_id.id
                                },
                            ), (0,0,
                                { 
                                    "type_examen_id" : type_examen_ef.id,
                                    "number": number,
                                    "matiere_id" : rec.matiere_id.id,
                                    "Pourcentage" : rec.pourcentage_exam,
                                    "coeficien" : rec.coeficien,
                                    "class_id" : rec.class_id.id,
                                    "unite_enseignement_id" : rec.unite_enseignement_id.id,
                                    "anne_academique_id" : rec.annee_academique_id.id,
                                    "semestre_id" : rec.semestre_id.id
                                },
                            ), (0,0,
                                { 
                                    "type_examen_id" : type_examen_pr.id,
                                    "number": number,
                                    "matiere_id" : rec.matiere_id.id,
                                    "Pourcentage" : rec.pourcentage_presence,
                                    "coeficien" : rec.coeficien,
                                    "class_id" : rec.class_id.id,
                                    "unite_enseignement_id" : rec.unite_enseignement_id.id,
                                    "anne_academique_id" : rec.annee_academique_id.id,
                                    "semestre_id" : rec.semestre_id.id
                                },
                            )
                    ]
                else:
                    rec.examen_registre_participant_ids = [
                            (0,0,
                                { 
                                    "type_examen_id" :  type_examen_cc.id,
                                    "number": number,
                                    "matiere_id" : rec.matiere_id.id,
                                    "Pourcentage" : rec.pourcentage_cc,
                                    "unite_enseignement_id" : rec.unite_enseignement_id.id,
                                    "coeficien" : rec.coeficien,
                                    "class_id" : rec.class_id.id,
                                    "anne_academique_id" : rec.annee_academique_id.id,
                                    "semestre_id" : rec.semestre_id.id
                                },
                            ), (0,0,
                                { 
                                    "type_examen_id" : type_examen_pr.id,
                                    "number": number,
                                    "matiere_id" : rec.matiere_id.id,
                                    "Pourcentage" : rec.pourcentage_presence,
                                    "coeficien" : rec.coeficien,
                                    "class_id" : rec.class_id.id,
                                    "unite_enseignement_id" : rec.unite_enseignement_id.id,
                                    "anne_academique_id" : rec.annee_academique_id.id,
                                    "semestre_id" : rec.semestre_id.id
                                },
                            )
                    ]

            if rec.matiere_id:
                unite_enseignement = self.env['education.unite.enseignement'].search([('semestre_id', '=',rec.semestre_id.id)], offset=0, limit=None, order=None, count=False)
                for line in unite_enseignement:
                    if line.syllabus_ids.subject_id == rec.matiere_id:
                        rec.unite_enseignement_id = line.id
            rec.state="validated"
            if rec.state == "validated":
                return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'type': 'success',
                                'message': "Régistre validé avec succès !",
                                'next': {'type': 'ir.actions.act_window_close'},
                            }
                        }

    @api.depends('examen_registre_participant_ids')
    def action_confirm(self):
        for rec in self:
            if rec.examen_registre_participant_ids:
                rec.state="confirm"
                if rec.state == "confirm":
                    return {
                                'type': 'ir.actions.client',
                                'tag': 'display_notification',
                                'params': {
                                    'type': 'success',
                                    'message': "Régistre confirmé avec succès !",
                                    'next': {'type': 'ir.actions.act_window_close'},
                                }
                            }
            else:
                raise ValidationError("Veuillez ajouter un type")

class ExamenRegistreLine(models.Model):
    _name = 'siantou.ems.examen.registre.line'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char('code')

    type_examen_id = fields.Many2one('siantou.ems.type.examen', string="Type d'examen",tracking=True)

    number = fields.Integer("Nombre d'étudiant")

    semestre_id = fields.Many2one('education.semestre', string='Semestre',tracking=True)

    anne_academique_id = fields.Many2one('education.academic.year', string='Année académique',tracking=True)

    matiere_id = fields.Many2one('education.subject', string='Matiere', tracking=True)

    class_id = fields.Many2one('education.class.division', string='Classe', tracking=True)

    student_class_ids = fields.One2many('siantou.ems.examen.student.line', 'examen_student_number_id')

    coeficien = fields.Float('Crédit', required=True)

    unite_enseignement_id = fields.Many2one('education.unite.enseignement', readonly=True, string='Unité d\'enseignement')

    Pourcentage = fields.Integer('Pourcentage')

    examen_registre_id = fields.Many2one('siantou.ems.examen.registre')

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validated', 'Valider'),
        ('confirm', 'Confirmer')
    ], string='state', default="draft")

    @api.depends('class_id')
    def action_validate(self):
        for rec in self:
            # Vérification du type d'examen
            if rec.type_examen_id.code == "PR":
                # Traitement spécifique pour le type d'examen "PR"
                if rec.class_id:
                    student_ids = self.env['oe.school.student'].search([('class_id', '=', rec.class_id.id)])
                    # Nettoyage des étudiants existants
                    if rec.student_class_ids:
                        rec.student_class_ids.unlink()
                    # Préparer les nouvelles lignes d'étudiants
                    new_student_lines = []
                    # Calcul de la note de présence pour chaque étudiant
                    for student in student_ids:
                        # Calculer le taux de présence
                        seances = self.env['education.attendance.sheet'].search([
                            ('subject_id', '=', rec.matiere_id.id),
                            ('class_id', '=', rec.class_id.id)
                        ])
                        total_heures = sum(seance.nbr_heure for seance in seances)
                        heures_presences = sum(line.nbr_heure for line in self.env['education.attendance.line'].search([
                            ('student_id', '=', student.id),
                            ('subject_id', '=', rec.matiere_id.id),
                            ('present', '=', True)
                        ]))

                        taux_presence = (heures_presences * 100) / total_heures if total_heures > 0 else 0
                        note_presence = (taux_presence / 100) * 20 if taux_presence > 0 else 0
                        # Préparer les données de l'étudiant
                        student_data = {
                            "student_id": student.id,
                            "note": note_presence  # Note de présence uniquement pour PR
                        }
                        new_student_lines.append((0, 0, student_data))
                    # Assigner les nouvelles lignes d'étudiants
                    rec.student_class_ids = new_student_lines
                # Vérification et validation
                if rec.student_class_ids:
                    num = self.env["ir.sequence"].next_by_code("aft_examen.add_note")
                    rec.name = num
                    rec.state = "validated"
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': 'success',
                            'message': "Validé avec succès !",
                            'next': {'type': 'ir.actions.act_window_close'},
                        }
                    }
                else:
                    raise ValidationError("Veuillez ajouter les étudiants")
            else:
                # Traitement pour les autres types d'examen
                if rec.class_id:
                    student_ids = self.env['oe.school.student'].search([('class_id', '=', rec.class_id.id)])
                    # Nettoyage des étudiants existants
                    if rec.student_class_ids:
                        rec.student_class_ids.unlink()
                    # Préparer les nouvelles lignes d'étudiants
                    new_student_lines = [(0, 0, {"student_id": student.id}) for student in student_ids]
                    # Assigner les nouvelles lignes d'étudiants
                    rec.student_class_ids = new_student_lines
                # Vérification et validation
                if rec.student_class_ids:
                    num = self.env["ir.sequence"].next_by_code("iia_examen.add_note")
                    rec.name = num
                    rec.state = "validated"
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': 'success',
                            'message': "Validé avec succès !",
                            'next': {'type': 'ir.actions.act_window_close'},
                        }
                    }
                else:
                    raise ValidationError("Veuillez ajouter les étudiants")

    def action_confirm(self):
        """
        Action confirmer
        """
        for rec in self:
            for line in rec.student_class_ids:
                line._check_note()
            rec.state="confirm"
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

class ExamenStudentLine(models.Model):
    _name = 'siantou.ems.examen.student.line'

    student_id = fields.Many2one('oe.school.student', string='Étudiant')

    note = fields.Float('Note')

    examen_student_number_id = fields.Many2one('siantou.ems.examen.registre.line')

    @api.constrains('note')
    def _check_note(self):
        for rec in self:
            if rec.note < 0 or rec.note > 20:
                raise ValidationError("La note doit être comprise entre 0 et 20")

