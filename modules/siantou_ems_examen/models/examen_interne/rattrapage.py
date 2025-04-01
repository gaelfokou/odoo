# -*- coding: utf-8 -*-

from odoo import models, fields, api,tools, _
import logging
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger("++++++++++++++")

class Rattrage(models.Model):
    """
    Module pou gérer les rattrapages
    """
    _name = "rat.reg"
    _description = "Module pou gérer les rattrapages"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char('name')

    semestre_id = fields.Many2one('education.semestre', string='Semestre',required=True, tracking=True)

    class_id = fields.Many2one('education.class.division', string='Classe',required=True, tracking=True)

    anne_academique_id = fields.Many2one('education.academic.year', string='Année académique', required=True, tracking=True)

    date = fields.Date(string="Date",default=lambda self: fields.Date.today())

    rat_ids = fields.One2many('rat.reg.ue', 'rat_reg_id')

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validate', 'Valider'),
        ('confirm', 'Confirmer'),
        ('cancel', 'Annuler'),
        ('done', 'Fait'),
    ], string='statut', default="draft")

    def action_validate(self):
        """
        fonction pour valider
        """
        array_ue = []
        for rec in self:
            num = self.env["ir.sequence"].next_by_code("aft_examen.rattrapage_registre")
            rec.name = num
            registre_obj = self.env['rat.reg.ue']
            syllabus_ids = self.env['education.syllabus'].search([('unite_enseignement_id.semestre_id','=',rec.semestre_id.id),('class_id','=',rec.class_id.class_id.id)])
            for data in syllabus_ids:
                array_ue.append({
                    "unite_enseignement_id" : data.unite_enseignement_id,
                })
            array_ue = list(
                {
                    dictionary["unite_enseignement_id"] : dictionary
                    for dictionary in syllabus_ids
                }.values()
            )
            for line in array_ue:
                registre_obj.create({
                    "class_id" : rec.class_id.id,
                    "semestre_id" : rec.semestre_id.id,
                    "anne_academique_id" : rec.anne_academique_id.id,
                    "ue_id" : line.unite_enseignement_id.id,
                    "rat_reg_id" : rec.id
                })
            rec.state = 'validate'
            if rec.state == "validate":
                return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'type': 'success',
                                'message': "Rattrapage validé avec succès !",
                                'next': {'type': 'ir.actions.act_window_close'},
                            }
                        }

    def action_confirm(self):
        """
        Fonction pour confirmer une action
        """
        for rec in self:
            rec.state = "confirm"
            if rec.state == "confirm":
                return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'type': 'success',
                                'message': "Rattrapage confirmé avec succès !",
                                'next': {'type': 'ir.actions.act_window_close'},
                            }
                        }

    def action_calcul(self):
        """
        Fonction pour ajouter les notes de rattrapages
        """
        type_examen_sn = self.env['siantou.ems.type.examen'].search([("code","=","SR")])

        for rec in self:
            for line in rec.rat_ids:
                if line.state != "confirm":
                    raise ValidationError("Veuillez confirmer les U.E")
                for sp in line.rat_sub_parent_ids:
                    if sp.state != "confirm":
                        raise ValidationError("Veuillez confirmer les matières parents !")
                for s in sp.rat_sub_ids:
                    if s.state != "confirm":
                        raise ValidationError("Veuillez confirmer les notes introduitent !")
            resultat_rattrapage = self.env["rat.reg.sub.parent"].search([
            ("anne_academique_id","=",rec.anne_academique_id.id),
            ("semestre_id","=",rec.semestre_id.id),
            ("class_id","=",rec.class_id.id),
            ])

            resultat_student = self.env["siantou.ems.examen.student"].search([
            ("anne_academique_id","=",rec.anne_academique_id.id),
            ("semestre_id","=",rec.semestre_id.id),
            ("class_id","=",rec.class_id.id),
            ])

            for std in resultat_student:
                for line in resultat_rattrapage.rat_sub_ids.rat_std_ids:
                    if std.student_id.id == line.student_id.id:
                        for mat in std.examen_student_line_ids.examen_student_subject_line_ids.examen_student_subject_ids:
                            if line.rat_sub_id.matiere_id.id == mat.matiere_id.id:
                                sn_note_found = False
                                for note in mat.examen_student_subject_ids:
                                    if note.type_examen_id.code == "SN":
                                        note.note = line.note_rattapage
                                        note.type_examen_id = type_examen_sn.id
                                        note.type_examen_id.name = type_examen_sn.name
                                        sn_note_found = True
                                        break
                                if not sn_note_found:
                                    for note in mat.examen_student_subject_ids:
                                        if note.type_examen_id.code == "CC":
                                            note.note = line.note_rattapage
                                            note.type_examen_id = type_examen_sn.id
                                            note.type_examen_id.name = type_examen_sn.name
                                            break 
                                    # if note.type_examen_id.code == "SN":
                                    #     note.note = line.note_rattapage
                                    #     note.type_examen_id = type_examen_sn.id
                                    #     note.type_examen_id.name = type_examen_sn.name
                                    # elif note.type_examen_id.code == "CC":
                                    #     note.note = line.note_rattapage
                                    #     note.type_examen_id = type_examen_sn.id
                                    #     note.type_examen_id.name = type_examen_sn.name
                            for s_mat in mat.examen_student_parent_subject_id.examen_student_subject_ids:
                                if s_mat.matiere_id.id == line.rat_sub_id.matiere_id.id:
                                    s_mat._compute_moyenne_matiere()
                            mat.examen_student_parent_subject_id._compute_moyenne_matiere_parent()
                            mat.examen_student_parent_subject_id._compute_moyenne_matiere_parent()
                            std.session = "SR"
                            mat.examen_student_parent_subject_id.examen_student_line_id._compute_credit()
                            mat.examen_student_parent_subject_id.examen_student_line_id._compute_moyenne()
                            mat.examen_student_parent_subject_id.examen_student_line_id.examen_student_id._compute_credit()
                            mat.examen_student_parent_subject_id.examen_student_line_id.examen_student_id._compute_moyenne()
                            mat.examen_student_parent_subject_id.examen_student_line_id.examen_student_id._compute_rang()
            rec.state = "done"
            if rec.state == "done":
                return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'type': 'success',
                                'message': "Calcul terminé avec succès !",
                                'next': {'type': 'ir.actions.act_window_close'},
                            }
                        }

    # def action_calcul(self):
    #     """
    #     Fonction pour ajouter les notes de rattrapages
    #     """
    #     type_examen_sn = self.env['siantou.ems.type.examen'].search([("code","=","SR")])

    #     for rec in self:
    #         for line in rec.rat_ids:
    #             if line.state != "confirm":
    #                 raise ValidationError("Veuillez confirmer les U.E")
    #             for emp in line.rat_sub_ids:
    #                 if emp.state != "confirm":
    #                     raise ValidationError("Veuillez confirmer les note introduitent !")
    #         resultat_rattrapage = self.env["rat.reg.sub"].search([
    #         ("anne_academique_id","=",rec.anne_academique_id.id),
    #         ("semestre_id","=",rec.semestre_id.id),
    #         ("class_id","=",rec.class_id.id),
    #         ])

    #         resultat_student = self.env["iia.examen.student"].search([
    #         ("anne_academique_id","=",rec.anne_academique_id.id),
    #         ("semestre_id","=",rec.semestre_id.id),
    #         ("class_id","=",rec.class_id.id),
    #         ])

    #         for std in resultat_student:
    #             for line in resultat_rattrapage.rat_std_ids:
    #                 if std.student_id.id == line.student_id.id:
    #                     for mat in std.examen_student_line_ids.examen_student_subject_line_ids:
    #                         if line.rat_sub_id.matiere_id.id == mat.matiere_id.id:
    #                             sn_note_found = False
    #                             for note in mat.examen_student_subject_ids:
    #                                 if note.type_examen_id.code == "SN":
    #                                     note.note = line.note_rattapage
    #                                     note.type_examen_id = type_examen_sn.id
    #                                     note.type_examen_id.name = type_examen_sn.name
    #                                     sn_note_found = True
    #                                     break
    #                             if not sn_note_found:
    #                                 for note in mat.examen_student_subject_ids:
    #                                     if note.type_examen_id.code == "CC":
    #                                         note.note = line.note_rattapage
    #                                         note.type_examen_id = type_examen_sn.id
    #                                         note.type_examen_id.name = type_examen_sn.name
    #                                         break 
    #                                 # if note.type_examen_id.code == "SN":
    #                                 #     note.note = line.note_rattapage
    #                                 #     note.type_examen_id = type_examen_sn.id
    #                                 #     note.type_examen_id.name = type_examen_sn.name
    #                                 # elif note.type_examen_id.code == "CC":
    #                                 #     note.note = line.note_rattapage
    #                                 #     note.type_examen_id = type_examen_sn.id
    #                                 #     note.type_examen_id.name = type_examen_sn.name
    #                         mat._compute_moyenne_matiere()
    #                         std.session = "SR"
    #                         mat.examen_student_line_id._compute_credit()
    #                         mat.examen_student_line_id._compute_moyenne()
    #                         mat.examen_student_line_id.examen_student_id._compute_credit()
    #                         mat.examen_student_line_id.examen_student_id._compute_moyenne()
    #                         mat.examen_student_line_id.examen_student_id._compute_rang()
            rec.state = "done"
            if rec.state == "done":
                return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'type': 'success',
                                'message': "Calcul terminé avec succès !",
                                'next': {'type': 'ir.actions.act_window_close'},
                            }
                        }

class RattrapageUe(models.Model):
    """
    Modèle pour gérer les UE pour un rattrapage
    """
    _name = "rat.reg.ue"
    _description = "Modèle pour gérer les UE pour un rattrapage"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char('name')

    ue_id = fields.Many2one('education.unite.enseignement', string='Unité d\'enseignement')

    anne_academique_id = fields.Many2one('education.academic.year', string='Année académiqu',  tracking=True)

    semestre_id = fields.Many2one('education.semestre', string='Semestre', tracking=True)

    class_id = fields.Many2one('education.class.division', string='Classe', tracking=True)

    date = fields.Date(string="Date",default=lambda self: fields.Date.today())

    rat_reg_id = fields.Many2one('rat.reg')

    rat_sub_parent_ids = fields.One2many('rat.reg.sub.parent', 'rat_ue_id', string='Matière Parent')

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validate', 'Valider'),
        ('confirm', 'Confirmer')
    ], string='statut', default="draft")

    def action_validate(self):
        """
        fonction pour valider
        """
        type_rattap = ["rpo","rpf"]
        subject_obj = {}
        for rec in self:
            num = self.env["ir.sequence"].next_by_code("aft_examen.rattrapage_ue")
            rec.name = num
            if rec.class_id and rec.semestre_id and rec.ue_id:
                syllabus_ids = self.env['siantou.ems.examen.student.subject.parent'].search([
                    ('examen_student_line_id.examen_student_id.semestre_id','=',rec.semestre_id.id),
                    ('examen_student_line_id.examen_student_id.class_id','=',rec.class_id.id),
                    ('examen_student_line_id.examen_student_id.anne_academique_id','=',rec.anne_academique_id.id),
                    ('examen_student_line_id.ue_id','=',rec.ue_id.id),
                    ('statut','in',type_rattap)])

                for line in syllabus_ids:
                    if line.matiere_parent_id.id not in subject_obj.keys():
                        subject_obj[line.matiere_parent_id.id] = {}
                        subject_obj[line.matiere_parent_id.id]["matiere_parent_id"] = line.matiere_parent_id.id
                        subject_obj[line.matiere_parent_id.id]["anne_academique_id"] = rec.anne_academique_id.id
                        subject_obj[line.matiere_parent_id.id]["class_id"] = rec.class_id.id
                        subject_obj[line.matiere_parent_id.id]["semestre_id"] = rec.semestre_id.id
                        subject_obj[line.matiere_parent_id.id]["coeficeint"] = line.coeficeint
                        subject_obj[line.matiere_parent_id.id]["rat_ue_id"] = rec.id

                rec.rat_sub_parent_ids.create(subject_obj.values())
            rec.state = 'validate'

    def action_confirm(self):
        """
        Fonction pour confirmer une action
        """
        for rec in self:

            rec.state = "confirm"

class RattrapageMatiereParent(models.Model):
    """
    Modèle pour gérer les matières parent d'un rattrapage
    """
    _name = "rat.reg.sub.parent"
    _description = "Modèle pour gérer les matières parent d'un rattrapage"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char('name')

    matiere_parent_id = fields.Many2one('education.under.subject', string='Matière Parent',tracking=True)

    anne_academique_id = fields.Many2one('education.academic.year', string='Année académique',  tracking=True)

    semestre_id = fields.Many2one('education.semestre', string='Semestre', tracking=True)

    class_id = fields.Many2one('education.class.division', string='Classe', tracking=True)

    rat_ue_id = fields.Many2one('rat.reg.ue')

    coeficeint = fields.Float('Coéficient')

    date = fields.Date(string="Date",default=lambda self: fields.Date.today())

    rat_sub_ids = fields.One2many('rat.reg.sub', 'rat_sub_parent_id', string='Sous-matière')

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validate', 'Valider'),
        ('confirm', 'Confirmer')
    ], string='statut', default="draft")

    def action_validate(self):
        """
        Fonction pour valider
        """
        type_rattap = ["rpo", "rpf"]
        subject_obj = {}

        for rec in self:
            num = self.env["ir.sequence"].next_by_code("aft_examen.rattrapage_sub_parent")
            rec.name = num

            if rec.class_id and rec.semestre_id and rec.matiere_parent_id:
                syllabus_ids = self.env["siantou.ems.examen.student.subject"].search([
                    ("examen_student_parent_subject_id.examen_student_line_id.examen_student_id.semestre_id", "=", rec.semestre_id.id),
                    ("examen_student_parent_subject_id.examen_student_line_id.examen_student_id.class_id", "=", rec.class_id.id),
                    ("examen_student_parent_subject_id.examen_student_line_id.examen_student_id.anne_academique_id", "=", rec.anne_academique_id.id),
                    ("examen_student_parent_subject_id.matiere_parent_id", "=", rec.matiere_parent_id.id),
                ])

                _logger.info("Syllabus_1: %s", rec.rat_ue_id.ue_id.id)
                _logger.info("Syllabus_1: %s", rec.semestre_id.id)
                _logger.info("Syllabus_2: %s", rec.class_id.id)
                _logger.info("Syllabus_3: %s", rec.anne_academique_id.id)
                _logger.info("Syllabus_4: %s", rec.matiere_parent_id.id)
                _logger.info("Syllabus_ids: %s", syllabus_ids)

                for line in syllabus_ids:
                    _logger.info("sous-matières_id: %s", line.matiere_id.under_subject_id.id)
                    if line.matiere_id.id not in subject_obj.keys() and line.statut in type_rattap and line.matiere_id.under_subject_id.name == rec.matiere_parent_id.name:
                        subject_obj[line.matiere_id.id] = {}
                        subject_obj[line.matiere_id.id]["matiere_id"] = line.matiere_id.id
                        subject_obj[line.matiere_id.id]["anne_academique_id"] = rec.anne_academique_id.id
                        subject_obj[line.matiere_id.id]["class_id"] = rec.class_id.id
                        subject_obj[line.matiere_id.id]["semestre_id"] = rec.semestre_id.id
                        subject_obj[line.matiere_id.id]["coeficeint"] = line.coeficeint
                        subject_obj[line.matiere_id.id]["rat_sub_parent_id"] = rec.id

                rec.rat_sub_ids.create(subject_obj.values())
                _logger.info("sous-matières: %s", rec.rat_sub_ids)

            rec.state = 'validate'

    def action_confirm(self):
        """
        Fonction pour confirmer une action
        """
        for rec in self:
            rec.state = "confirm"

class RattrapageMatiere(models.Model):
    """
    Modèle pour gérer les matière d'un rattrapage
    """
    _name = "rat.reg.sub"
    _description = "Modèle pour gérer les matière d'un rattrapage"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char('name')

    matiere_id = fields.Many2one('education.subject', string='Matière',tracking=True)

    anne_academique_id = fields.Many2one('education.academic.year', string='Année académiqu',  tracking=True)

    semestre_id = fields.Many2one('education.semestre', string='Semestre', tracking=True)

    class_id = fields.Many2one('education.class.division', string='Classe', tracking=True)

    rat_sub_parent_id = fields.Many2one('rat.reg.sub.parent')

    coeficeint = fields.Float('Coéficient')

    date = fields.Date(string="Date",default=lambda self: fields.Date.today())

    rat_std_ids = fields.One2many('rat.reg.std', 'rat_sub_id')

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validate', 'Valider'),
        ('confirm', 'Confirmer')
    ], string='statut', default="draft")

    def action_validate(self):
        """
        fonction pour valider
        """
        for rec in self:
            num = self.env["ir.sequence"].next_by_code("aft_examen.rattrapage_subject_parent")
            rec.name = num
            student_obj = self.env["siantou.ems.examen.student.subject"].search([
                ("examen_student_parent_subject_id.examen_student_line_id.examen_student_id.semestre_id","=",rec.semestre_id.id),
                ("examen_student_parent_subject_id.examen_student_line_id.examen_student_id.anne_academique_id","=",rec.anne_academique_id.id),
                ("examen_student_parent_subject_id.examen_student_line_id.examen_student_id.class_id","=",rec.class_id.id),
                ("matiere_id","=",rec.matiere_id.id),
                ])

            _logger.info(student_obj)

            student_dict = {}  # Dictionnaire pour stocker les informations des étudiants
            for line in student_obj:
                if line.statut != "valid" and line.statut != "ajour":
                    student_id = line.examen_student_parent_subject_id.examen_student_line_id.examen_student_id.student_id.id
                    if student_id not in student_dict:  # Vérifier si l'étudiant est déjà dans le dictionnaire
                        student_dict[student_id] = {
                            "student_id": student_id,
                            "statut": line.statut
                        }

            # Convertir le dictionnaire en liste et l'assigner à rec.rat_std_ids
            rec.rat_std_ids = [(0, 0, student_info) for student_info in student_dict.values()]

            _logger.info(rec.rat_std_ids)

            rec.state = 'validate'

    def action_confirm(self):
        """
        Fonction pour confirmer une action
        """
        for rec in self:
            for line in rec.rat_std_ids:
                if line.note_rattapage < 0 or line.note_rattapage > 20:
                    raise ValidationError("Une note doit être en te 0-20")
            rec.state = "confirm"

class RattrapageStudent(models.Model):
    """
    Modèle pour gérer les notes des étudiant
    """
    _name = "rat.reg.std"
    _description = " Modèle pour gérer les notes des étudiant"

    student_id = fields.Many2one('oe.school.student', string='Étudiant')

    statut = fields.Selection([
        ('rpo', 'Rattrapage obligatoire'),
        ('rpf', 'Rattrapage facultatif')
    ], string='statut')

    note_rattapage = fields.Float('Note de rattrapage')

    rat_sub_id = fields.Many2one('rat.reg.sub')

