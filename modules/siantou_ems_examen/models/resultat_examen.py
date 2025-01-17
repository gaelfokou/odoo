# -*- coding: utf-8 -*-
from odoo import models, fields, api
from babel.dates import format_date
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError



import logging
_logger = logging.getLogger("++++++++++++")



class ResultatSubjectExamen(models.Model):
    _name = 'examen.resultat.subject'
    _description = "Model pour gérer les résultats des matières des examen"
    _inherit = ["mail.thread", "mail.activity.mixin"]


    name = fields.Char(
        'Libellé', 
        required=True,
    )
    year_id = fields.Many2one(
        'siantou.ems.core.year',
        string='Année académique', 
        required=True,
    )
    semester_id = fields.Many2one(
        'siantou.ems.core.year.semester',
        string='Semestre', 
        required=True,
    )
    field_of_study_id = fields.Many2one(
        'siantou.ems.core.field_of_study', 
        string="Filière", 
        required=True,
    )
    level_id = fields.Many2one(
        'siantou.ems.core.level',
        string='Niveau',
        required=True,
    )
    type_examen_id = fields.Many2one(
        'siantou.ems.examen.type',
        "Type d'examen",
        required=True,
    )
    # exam_session_id = fields.Many2one(
    #     'siantou.ems.examen.session',
    #     string="Examen concerné", 
    #     required=True, 
    # )
    exam_subject_id = fields.Many2one(
        'examen.session.line.subject',
        'Matière',
        required=True,
    )
    exam_subject_domain = fields.Binary(store=False)
    show_field = fields.Boolean(default=False)
    show_mark = fields.Boolean(default=False)
    state = fields.Selection([
            ('no_note', 'Aucune note disponible'), 
            ('note', 'Note disponible')
        ],
        default="no_note"
    )
    result_subject_line_ids = fields.One2many(
        'examen.resultat.subject.line',
        'result_subject_id',
        string="Notes des étudiants",
    )


    @api.onchange('type_examen_id')
    def onchange_subject_id(self):
        for rec in self:
            if (rec.year_id and 
                rec.field_of_study_id and 
                rec.semester_id and 
                rec.type_examen_id and 
                rec.level_id):
                rec.exam_subject_domain = [
                    ('exam_id.type_examen_id', '=', rec.type_examen_id.id),
                    ('field_of_study_id', '=', rec.field_of_study_id.id),
                    ('year_id', '=', rec.year_id.id),
                    ('exam_id.semester_id', '=', rec.semester_id.id),
                    ('level_id', '=', rec.level_id.id),
                ]
                rec.show_field = True
            else:
                rec.exam_subject_domain = []
                rec.show_field = False
                # raise ValidationError("Merci de Sélectionner : l'année académique, le semestre, le niveau, le filière")


    @api.onchange('exam_subject_id')
    def onchange_exam_subject_id(self):
        for rec in self:
            if (rec.exam_subject_id):
                rec.name = f"Résultat_{rec.exam_subject_id.name}"


    def button_show_resultat(self):
        for rec in self:
            if rec.exam_subject_id:
                rec.result_subject_line_ids.unlink()
                student_results = []
                anonymous_id = self.env['examen.subject.rating.anonymous'].search(
                    [
                        ('exam_session_id', '=', rec.exam_subject_id.exam_id.id),
                        ('exam_subject_id', '=', rec.exam_subject_id.id),
                        ('state', '=', 'done'),
                    ],limit=1
                )
                _logger.info(rec.exam_subject_id.exam_id.type_examen_id.code)
                _logger.info(anonymous_id.anonymous_code_ids)
                if len(anonymous_id.anonymous_code_ids)>0:
                    for mark_id in anonymous_id.anonymous_code_ids:
                        # _logger.info(mark_id.student_id.name)
                        # _logger.info(mark_id.marks)
                        # _logger.info(mark_id.exam_grade_line_id.name)
                        student_results.append({
                            'result_subject_id':rec.id,
                            'student_id':mark_id.student_id.id,
                            'note':mark_id.marks
                        })
                    _logger.info(student_results)
                    #========== add line resultat subject in database
                    for student in student_results:
                        rec.result_subject_line_ids.create(student)
                    
                    if len(rec.result_subject_line_ids)>0:
                        rec.show_mark=True
                        rec.update({
                            "state":"note"
                        })
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'type': 'success',
                                'message': "Récupération des données réussis",
                                'next': {'type': 'ir.actions.act_window_close'},
                            }
                        }
                else:
                    raise ValidationError("Codification ou remplissage des notes non trouvé")



    def button_print_pdf_resultat(self):
        for rec in self:
            if len(rec.result_subject_line_ids)>0:
                student_marks = []
                for mark_id in rec.result_subject_line_ids:
                    student_marks.append({
                        'student_name':mark_id.student_id.name,
                        'note':mark_id.note,
                    })
            else:
                raise ValidationError("Impossible de télécharger le fichier : Notes non trouvés")

            data = {
                # 'ids':rec.ids,
                'model':rec,
                'acad':{
                    'cycle_name':rec.field_of_study_id.cursus_id.name,
                    'field_of_study_name':rec.field_of_study_id.name,
                    'type_examen':rec.type_examen_id.name,
                    'year_name':rec.year_id.name,
                    'exam_subject_name':rec.exam_subject_id.subject_id.name,
                },
                'marks':student_marks,
                'date': fields.date.today(),
            }
            _logger.info(data)
            report_action = self.env.ref('siantou_ems_examen.action_report_student_examen_mark_pdf')
            return report_action.report_action(self,data=data)



class ResultatSubjectLineExamen(models.Model):
    _name = 'examen.resultat.subject.line'
    _description = "Model pour gérer les lines des résultats des matières des examens"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'student_id'

    result_subject_id = fields.Many2one(
        comodel_name='examen.resultat.subject',
        string="Résultat", required=True, ondelete='cascade', 
        index=True, copy=False,
    )
    student_id = fields.Many2one(
        comodel_name='oe.school.student',
        string="Etudiant", 
        required=True, 
        ondelete='cascade', 
        index=True, copy=False,
    )
    note = fields.Float(string="Note")
    # note_sn = fields.Float(string="Note de SN")
    # note_final = fields.Float(string="Note finale")
    












