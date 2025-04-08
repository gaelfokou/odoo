# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError


class ClassroomBuilding(models.Model):
    _name = 'oe.school.building'
    _description = 'Bâtiments'
    _order = 'name'

    active = fields.Boolean(default=True)
    name = fields.Char(string="Bâtiment", required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    address_id = fields.Many2one('res.partner', required=True, string="Campus", domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")


class ClassroomBuildingRoom(models.Model):
    _name = 'oe.school.building.room'
    _description = 'Salles de classe'
    _order = 'name'
    
    name = fields.Char(string='Nom de la salle', required=True, index=True, translate=True)
    building_id = fields.Many2one('oe.school.building', string='Bâtiment', required=True, index=True, )
    capacity = fields.Integer(string='Capacité', required=True, default=10)

