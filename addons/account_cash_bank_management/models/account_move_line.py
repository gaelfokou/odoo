from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    ecole_id = fields.Many2one('siantou.ems.core.school', related='move_id.ecole_id', store=True)
    departement_id = fields.Many2one('hr.department', related='move_id.departement_id', store=True)
    filiere_id = fields.Many2one('siantou.ems.core.field_of_study', related='move_id.filiere_id', store=True)
    specialite_id = fields.Many2one('siantou.ems.core.specialty', related='move_id.specialite_id', store=True)
    annee_academique_id = fields.Many2one('siantou.ems.core.year', related='move_id.annee_academique_id', store=True)
    cycle_id = fields.Many2one('oe.school.course', related='move_id.cycle_id', store=True)
    niveau_id = fields.Many2one('siantou.ems.core.level', related='move_id.niveau_id', store=True)
    semestre_id = fields.Many2one('siantou.ems.core.year.semester', related='move_id.semestre_id', store=True)
