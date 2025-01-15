# -*- coding: utf-8 -*-

from babel.dates import format_date
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger("++++++++++++")



class ExamRatingAnonymousMark(models.Model):
    _name = 'subject.mark'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = ""

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Les notes existe déjà pour cette codification'),
    ]
    

    name = fields.Char(string="Libellé")
    exam_subject_mark_id = fields.Many2one(
        comodel_name='examen.subject.rating.anonymous',
        string="Codification d'examen", 
        required=True, 
        index=True, 
        copy=False,
    )
    anonymous_code_ids = fields.Many2many(
        'examen.subject.rating.anonymous.result',
        string="Codification d'examen", 
        required=True, 
    )


    @api.onchange('exam_subject_mark_id')
    def _onchange_exam_subject_mark_id(self):
        for rec in self:
            rec.name = f"Note_de_{rec.exam_subject_mark_id.exam_subject_id.name}"
            rec.anonymous_code_ids = rec.exam_subject_mark_id.anonymous_code_ids




class ExamRatingAnonymous(models.Model):
    _name = 'examen.subject.rating.anonymous'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = "Note de l'examen"


    name = fields.Char(string="Nom", required=True)
    exam_session_id = fields.Many2one(
        comodel_name='siantou.ems.examen.session',
        string="Session d'examen", 
        required=True, 
        ondelete='cascade', 
        index=True, copy=False,
        domain="[('state','=','progress')]"
    )
    exam_id = fields.Many2one(
        comodel_name='examen.session.line',
        string="Liste des examens programmées", 
        required=True, 
        ondelete='cascade', 
        index=True, 
        copy=False,
        domain=[('id','=',False)]
    )
    exam_subject_id = fields.Many2one(
        comodel_name='examen.session.line.subject',
        string="Liste des matières programmées", 
        ondelete='cascade', 
        index=True, 
        copy=False,
        domain=[('id','=',False)]
    )
    anonymous_code_ids = fields.One2many('examen.subject.rating.anonymous.result', 'anonymous_id')
    exam_request_domain = fields.Binary(default=0, store=False) 
    exam_subject_request_domain = fields.Binary(default=0, store=False) 
    

    @api.onchange('exam_session_id')
    def _onchange_exam_session_id(self):
        for rec in self:
            if rec.exam_session_id:
                rec.exam_request_domain = [
                    ('exam_session_id','=',rec.exam_session_id.id),
                ]


    @api.onchange('exam_id')
    def _onchange_exam_id(self):
        for rec in self:
            if rec.exam_id:
                rec.exam_subject_request_domain = [
                    ('exam_id','=',rec.exam_id.id),
                ]


    def create(self, values):
        # raise ValidationError("eeeeeee rr")
        res = super(ExamRatingAnonymous, self).create(values)
        _logger.info(res.id)
        _logger.info(res.exam_subject_id.id)
        _logger.info(res.exam_subject_id.exam_attendee_ids)

        for attendee_id in res.exam_subject_id.exam_attendee_ids:
            _logger.info(attendee_id.student_id.name)
            self.env['examen.subject.rating.anonymous.result'].create({
                'anonymous_id':res.id,
                'student_id':attendee_id.student_id.id,
            })

        return res

        # @api.model
        # def create(self, values):
        #     # CODE HERE
        #     return super(ClassName, self).create(values)



class ExamRatingAnonymousResult(models.Model):
    _name = 'examen.subject.rating.anonymous.result'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = "Note de l'examen"
    _rec_name = 'student_id'


    anonymous_id = fields.Many2one(
        comodel_name='examen.subject.rating.anonymous',
        string="Codification", 
        ondelete='cascade', 
        index=True, 
        copy=False
    )
    student_id = fields.Many2one(
        comodel_name='oe.school.student',
        string="Etudiant", 
        required=True, 
        change_default=True, 
        ondelete='restrict', 
    )
    anonyma_code = fields.Char(
        string="Code anonyma",
    )
    # attendance_status = fields.Selection([
    #         ('P', 'Présent'),
    #         ('A', 'Abscent'),
    #     ], 
    #     string='Type de présence',
    #     required=True,
    #     readonly="exam_state != 'prepare'"
    # )
    marks = fields.Float(
        string='Note obtenue', 
    )
    exam_grade_line_id = fields.Many2one(
        'siantou.ems.examen.grade', 
        string='Examen Grade', 
        store=True,
        compute='_compute_exam_grade'
    )
    
    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True, index=True,
        default=lambda self: self.env.company
    )


    # ----------------------------------------
    # Constrains
    # ----------------------------------------
    @api.constrains('marks')
    def _check_marks_range(self):
        for record in self:
            if record.marks > record.anonymous_id.exam_subject_id.exam_id.exam_session_id.type_examen_id.prcent_note:
                raise ValidationError(
                    f"Les notes obtenues ne doivent pas être supérieur à {record.exam_subject_id.exam_id.exam_session_id.type_examen_id.prcent_note}."
                )


    # @api.onchange('attendance_status')
    # def onchange_attendance_status(self):
    #     student_attende_id = self.env['session.line.attende'].search(
    #         [
    #             ('exam_subject_id','=',self.exam_subject_id.id),
    #             ('student_id','=',self.student_id.id),
    #         ],
    #         limit=1
    #     )
    #     self.attendance_status = student_attende_id.status


    # CRUD Operations
    
    #compute Methods
    @api.depends('marks')
    def _compute_exam_grade(self):
        for result in self:
            result.exam_grade_line_id = False
            grade_lines = self.env['siantou.ems.examen.grade'].search([],order='score_min DESC')
            for line in grade_lines:
                if result.marks in [line.score_min, line.score_max]:
                    result.exam_grade_line_id = line.id
                    break

        
    