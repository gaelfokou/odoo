# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, tools, _

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

    year_id = fields.Many2one(
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
        for record in self:
            if record.class_id:
                classes = self.env['siantou.ems.core.class'].search([('id', '=', record.class_id.id)]) 

                if len(record.syllabus_ids) > 0: # Effacer les lignes du syllabus si la classe n'est pas défini
                    for elt in record.syllabus_ids:
                        elt.unlink()

                for classe in classes:
                    for ue in classe.ue_ids:
                        for mat in ue.subject_ids:
                            record.syllabus_ids = [
                                (
                                    0,
                                    0,
                                    {
                                        "class_id": record.class_id.id,
                                        "ue_id": ue.id,
                                        "subject_id": mat.id,
                                    },
                                )
                            ]
