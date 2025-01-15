# -*- coding: utf-8 -*-

from odoo import models, fields, api


class TypeExamen(models.Model):
    _name = 'siantou.ems.examen.type'
    _description = "Model pour gerer le type d'examen"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    code = fields.Char('Code', required=True, tracking=True)
    name = fields.Char('Nom', required=True, tracking=True)
    prcent_note = fields.Float(string="Pourcentage sur la note")


class TypeRattrappageExamen(models.Model):
    _name = 'siantou.ems.examen.type.rattrapage'
    _description = "Model pour gerer le type d'examen de rattrapage"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char('Nom', required=True, tracking=True, store=True)
    type_examen_id = fields.Many2one(
        'siantou.ems.examen.type',
        string='type_examen',
        required=True
    )

    _sql_constraints = [
        ('unique_name', 'unique(name)', "Ce nom existe déjà")
    ]

    @api.onchange('type_examen_id')
    def onchange_name(self):
        for type_rattrap in self:
            name = f"rattrapage"
            if type_rattrap:
                name = f"{name}_{type_rattrap.type_examen_id.code}"
            
            type_rattrap.name=name












