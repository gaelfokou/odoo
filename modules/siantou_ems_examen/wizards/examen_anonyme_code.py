from babel.dates import format_date
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger("++++++++++++")


class ResulteWizard(models.TransientModel):
    _name = "examen.session.line.result.wizard"

    exam_subject_id = fields.Many2one(
        comodel_name='examen.session.line.subject',
        string="Examen", 
        required=True, 
        ondelete='cascade', 
        index=True, 
        copy=False
    )
    results = fields.One2many('examen.session.line.result.wizard.line','result_id')

    @api.model
    def default_get(self, fields):
        res = super(ResulteWizard, self).default_get(fields)
        if self.env.context.get('active_id'):
            # results = self.env['examen.session.line.result'].search([
            #     ('exam_subject_id','=', self.env.context.get('active_id'))
            # ])
            res['exam_subject_id'] = self.env.context.get('active_id')
            # self.write({'results': [(6, 0, results.ids)]})
        return res


class ResulteWizardLine(models.TransientModel):
    _name = "examen.session.line.result.wizard.line"

    result_id = fields.Many2one('examen.session.line.result.wizard')
    student_id = fields.Many2one(
        comodel_name='oe.school.student',
        string="Etudiant", 
        required=True, 
    )
    anonyma_code = fields.Char(
        string="Code anonyma",
    )