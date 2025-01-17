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
    anonymous_code_mark_ids = fields.Many2many(
        'examen.subject.rating.anonymous.result',
        string="Codification d'examen", 
        required=True, 
    )


    @api.onchange('exam_subject_mark_id')
    def _onchange_exam_subject_mark_id(self):
        for rec in self:
            rec.name = f"Note_de_{rec.exam_subject_mark_id.exam_subject_id.name}"
            rec.anonymous_code_mark_ids = rec.exam_subject_mark_id.anonymous_code_ids




class ExamRatingAnonymous(models.Model):
    _name = 'examen.subject.rating.anonymous'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = "Note de l'examen"


    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Les notes existe déjà pour cette codification'),
    ]

    name = fields.Char(string="Nom", required=True)
    exam_session_id = fields.Many2one(
        comodel_name='siantou.ems.examen.session',
        string="Session d'examen", 
        required=True, 
        ondelete='cascade', 
        index=True, copy=False,
        domain="[('state','=','progress')]"
    )
    exam_subject_id = fields.Many2one(
        comodel_name='examen.session.line.subject',
        string="Matières programmées", 
        ondelete='cascade', 
        index=True, 
        copy=False,
        domain=[('id','=',False)]
    )
    state = fields.Selection([
            ('create', 'Encours de création'),
            ('done', 'Crée'),
        ], 
        string='Statut', 
        tracking=True
    )
    anonymous_code_ids = fields.One2many('examen.subject.rating.anonymous.result', 'anonymous_id')
    exam_subject_request_domain = fields.Binary(default=0, store=False) 


    @api.onchange('exam_session_id', 'exam_subject_id')
    def _onchange_name(self):
        for rec in self:
            name = f"Codification_note"
            if rec.exam_subject_id:
                name = f"{name}_{rec.exam_subject_id.name}"
            rec.name=name


    @api.onchange('exam_session_id')
    def _onchange_exam_session_id(self):
        for rec in self:
            if rec.exam_session_id:
                rec.exam_subject_request_domain = [
                    ('exam_id','=',rec.exam_session_id.id),
                ]


    def create(self, values):
        # raise ValidationError("eeeeeee rr")
        res = super(ExamRatingAnonymous, self).create(values)
        res.update({
            'state':'done'
        })
        res.exam_subject_id.update({
            'state':'code'
        })
        for attendee_id in res.exam_subject_id.exam_attendee_ids:
            self.env['examen.subject.rating.anonymous.result'].create({
                'anonymous_id':res.id,
                'student_id':attendee_id.student_id.id,
            })

        return res


class ExamRatingAnonymousResult(models.Model):
    _name = 'examen.subject.rating.anonymous.result'
    _inherit = ['portal.mixin', 'mail.thread', 
        'mail.activity.mixin', 'utm.mixin']
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
    state = fields.Selection([
            ('create', 'Encours de création'),
            ('add', 'Crée'),
            ('done', 'Note remplis'),
        ], 
        string='Statut', 
        tracking=True
    )
    marks = fields.Float(
        string='Note obtenue', 
    )
    exam_grade_line_id = fields.Many2one(
        'siantou.ems.examen.grade', 
        string='Examen Grade', 
        store=True,
        compute='_compute_exam_grade'
    )
    is_marks_ok = fields.Boolean(default=False)
    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True, index=True,
        default=lambda self: self.env.company
    )

    @api.onchange('marks')
    def onchange_mark(self):
        for rec in self:
            self.marks = rec.marks
            rec.state = 'done'
            _logger.info(rec.state)
    

    def check_marks_subject(self, anonymous_id):
        results = self.env['examen.subject.rating.anonymous.result'].search(
            [('anonymous_id', '=', anonymous_id.id)]
        )
        for rec in results:
            if rec.state=='add' or rec.state=='create':
                raise ValidationError(f"Certaines notes dans {anonymous_id.name} ne sont pas fournis")
    


    def create(self, values):
        res = super().create(values)
        _logger.info(res.state)
        return res
    # ----------------------------------------
    # Constrains
    # ----------------------------------------
    @api.constrains('marks')
    def _check_marks_range(self):
        for record in self:
            _logger.info(record.anonymous_id.exam_session_id.name)
            if record.marks not in range(1,21):
                raise ValidationError(
                    f"Les notes obtenues ne doivent pas être comprise entre 1 et 20."
                )





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

        
    