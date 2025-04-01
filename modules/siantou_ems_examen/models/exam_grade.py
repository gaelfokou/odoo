# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ExamGrade(models.Model):
    _name = 'siantou.ems.examen.grade'
    _description = "Grade de l'examen"
    _order = "name asc"

    name = fields.Char(string='Grade', required=True)
    note = fields.Float(string='Note /4', required=True)
    score_min = fields.Float(string='Moyenne min', required=True)
    score_max = fields.Float(string='Moyenne max', required=True)
    appreciation = fields.Char(string='Appréciaiton', required=True)

