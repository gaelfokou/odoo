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
            

class ExamenDateButtoire(models.Model):
    _name = 'siantou.ems.examen.date.butoire'
    _description = "Model pour gerer les dates butoires des examens"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    code = fields.Char('Code', required=True, tracking=True)
    name = fields.Char('Nom', required=True, tracking=True)
    date = fields.Datetime('Date butoire')
    type_examen_id = fields.Many2one('siantou.ems.examen.type', string='Type d\'examen')
    annee_acadmique_id = fields.Many2one('siantou.ems.core.year', string='Année Académique')
    semestre_id = fields.Many2one('siantou.ems.core.year.semester', string='Semestre', required=True, tracking=True)
    school_id = fields.Many2one('siantou.ems.core.school', string='Ecole')
    class_ids = fields.Many2many('siantou.ems.core.class', string='Classe')
            
    @api.onchange('school_id')
    def _onchange_school_id(self):
        if self.school_id:
            # Récupérer les classes associées à l'école sélectionnée
            classes = self.env['siantou.ems.core.class'].search([
                ('school_id', '=', self.school_id.id)
            ])
            # Remplir le champ des classes avec les IDs des classes trouvées
            self.class_ids = [(6, 0, classes.ids)]
        else:
            # Si aucune école n'est sélectionnée, vider le champ des classes
            self.class_ids = [(5, 0, 0)]












