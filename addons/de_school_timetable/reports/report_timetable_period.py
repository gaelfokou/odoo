# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class ReprotTimetable_period(models.Model):
    _name = "oe.report.timetable.period"
    _description = "Rapport périodique"
    _auto = False
    
    dayofweek = fields.Char('Jour de la semaine', readonly=True)
    day_period = fields.Char('Période de jour', readonly=True)
    company_id = fields.Many2one('res.company', string='Université', readonly=True)
    date = fields.Date(string='Date', readonly=True)
    course_id = fields.Many2one('oe.school.course', string='Cursus', readonly=True)
    batch_id = fields.Many2one('oe.school.course.batch', string='Lot', readonly=True)
    subject_id = fields.Many2one('oe.school.subject', string='COurs', readonly=True)
    teacher_id = fields.Many2one('hr.employee', string='Enseignant', readonly=True)
    hour_from = fields.Float(string='De', readonly=True)
    hour_to = fields.Float(string='A', readonly=True)
    
    def _pr(self):
        pr_str = """
        select tt.id, tt.dayofweek, tt.hour_from, tt.hour_to, 
        c.id as company_id,
        tt.date, tt.course_id, tt.batch_id, tt.subject_id, tt.teacher_id
from oe_school_timetable tt
join res_company c on c.id = tt.company_id
where c.is_school = True
        """
        return pr_str

    def _from(self):
        return """(%s)""" % (self._pr())

    def _get_main_request(self):
        request = """
            CREATE or REPLACE VIEW %s AS
                SELECT id AS id,
                dayofweek,
                company_id,
                hour_from,
                hour_to,
                date,
                course_id,
                batch_id,
                subject_id,
                teacher_id
                FROM %s
                AS foo""" % (self._table, self._from())
        return request

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(self._get_main_request())

        
    