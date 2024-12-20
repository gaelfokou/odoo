# -*- coding: utf-8 -*-

from odoo import models, fields, api,tools, _
import logging
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger("++++++++++++++")

class ConditionAdmission(models.Model):
    """
    Modèle pour enregistrer les condition d'admission
    """
    _name = "siantou.ems.condition.admission"
    _description = " Modèle pour enregistrer les condition d'admission"


    nationality_id = fields.Many2one('res.country', string='Nationalité',required=True,tracking=True)

    nombre = fields.Integer('Nombre par pays',required=True,tracking=True)
    
    nbre_attente = fields.Integer("Liste d'attente",tracking=True)

    # registre_id = fields.Many2one('siantou.session.registre', string="Régistre", readonly=True)