# -*- coding: utf-8 -*-
import logging

from odoo import fields, models, api, _


_logger = logging.getLogger("++++++++++++++++++++++++++++++++++++++++++")


class ProductionDpo(models.Model):
    _name = 'production.pe'
    _description = 'Production du PROGRAMME D\'ENSEIGNEMENT'

    _rec_name = 'name'
    _order = 'name ASC'

    name = fields.Char(
        string='Name',
        default=lambda self: _('New'),
        copy=False
    )
    
    annee_academique_id = fields.Many2one(
        string='annee_academique',
        comodel_name='siantou.ems.core.year',
        required=True,
    )

    class_id = fields.Many2one(
        string='Classe',
        comodel_name='siantou.ems.core.class',
        required=True,
    )

    
    description = fields.Text(
        string='Description',
    )
    
    
    semestre_id = fields.Many2one(
        string='Semestre',
        comodel_name='siantou.ems.core.year.semester',
    )
    
    syllabus_ids = fields.One2many(
        string='syllabus',
        comodel_name='siantou.ems.core.syllabus',
        inverse_name='pro_pe_id',
    )    
     
    @api.onchange('class_id')
    def _onchange_class(self):
        for rec in self:
            if rec.class_id:
                datas = []
                semestre_obj = self.env['siantou.ems.core.year.semester'].search([('class_id','=',rec.class_id.id)])
                if len(rec.syllabus_ids) > 0: # Effacer les lignes du syllabus si la classe ou le semestre n'est pas défini
                    for elt in rec.syllabus_ids:
                        elt.unlink()
                for line in semestre_obj:
                    for ue in line.unite_enseignement_ids:
                        for mat in ue.subject_ids:
                            rec.syllabus_ids = [
                                (
                                    0,
                                    0,
                                    {
                                        "class_id":rec.class_id.id,
                                        "unite_enseignement_id" : ue.id,
                                        "subject_id":mat.id,
                                    },
                                )
                            ]
                            