# -*- coding: utf-8 -*-
import logging

from odoo import fields, models, api, _

_logger = logging.getLogger(__name__)

class ProductionDpo(models.Model):
    _name = 'production.pe'
    _description = 'Production du PROGRAMME D\'ENSEIGNEMENT'

    _rec_name = 'name'
    _order = 'name asc'

    name = fields.Char(
        string='Name',
        default=lambda self: _('New'),
        copy=False
    )

    annee_academique_id = fields.Many2one(
        'siantou.ems.core.year',
        string='annee_academique',
        required=True,
    )

    class_id = fields.Many2one(
        'siantou.ems.core.class',
        string='Classe',
        required=True,
    )

    description = fields.Text(
        string='Description',
    )

    syllabus_ids = fields.One2many(
        'siantou.ems.core.syllabus',
        'pro_pe_id',
        string='syllabus',
    )

    @api.onchange('class_id')
    def _onchange_class_id(self):
        for rec in self:
            if rec.class_id:
                classes_obj = self.env['siantou.ems.core.class'].search([('id', '=', rec.class_id.id)]) 

                if len(rec.syllabus_ids) > 0: # Effacer les lignes du syllabus si la classe n'est pas défini
                    for elt in rec.syllabus_ids:
                        elt.unlink()

                for line in classes_obj:
                    for ue in line.ue_ids:
                        for mat in ue.subject_ids:
                            rec.syllabus_ids = [
                                (
                                    0,
                                    0,
                                    {
                                        "class_id": rec.class_id.id,
                                        "ue_id" : ue.id,
                                        "subject_id": mat.id,
                                    },
                                )
                            ]
