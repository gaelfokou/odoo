# -*- coding: utf-8 -*-

from babel.dates import format_date
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class ExamAttendees(models.Model):
    _name = 'session.line.attende'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = "Participants à l'examen"
    _rec_name = 'student_id'

    exam_subject_id = fields.Many2one(
        comodel_name='examen.session.line.subject',
        string="Examen", 
        required=True, 
        ondelete='cascade', 
        index=True, 
        copy=False
    )
    student_id = fields.Many2one(
        comodel_name='oe.school.student',
        string="Etudiant", 
        required=True, 
        ondelete='restrict', 
    )
    exam_state = fields.Selection(
        related='exam_subject_id.state', 
        store=True
    )
    status = fields.Selection([
            ('P', 'Présent(e)'),
            ('A', 'Absent(e)'),
        ],
        string='Statut', 
    )

    def Mark_attendance(self):
        return {
            'name': 'Marquer la présence',
            'view_mode': 'form',
            'res_model': 'session.line.attende.attend',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }