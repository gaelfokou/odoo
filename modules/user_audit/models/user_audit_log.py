# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models
from odoo.tools import date_utils
import json

class UserAuditLogs(models.Model):
    """ For tracking user activity by adding user logs """
    _name = "user.audit.log"
    _description = "User Audit Details"

    name = fields.Char(string="Reference", required=True, readonly=True,
                       default='New', help="For getting reference")
    user_id = fields.Many2one('res.users', string="User",
                              help="For getting user")
    record = fields.Integer(string="Record ID",
                            help="For getting which record has accessed")
    model_id = fields.Many2one('ir.model', string="Object",
                               help="For getting which model has accessed")
    operation_type = fields.Selection(selection=[('read', 'Read'),
                                                 ('write', 'Write'),
                                                 ('create', 'Create'),
                                                 ('delete', 'Delete')],
                                      string="Type",
                                      help="For getting which operation has "
                                           "been performed")
    date = fields.Datetime(string="Date",
                           help="For getting which time the operation has done")
    record_name = fields.Char(string="Record name",
                            compute='_compute_name', store=True,
                            help="For getting record name")
    record_description = fields.Text(string="Record description",
                            compute='_compute_description', store=True,
                            help="For getting record description")

    @api.depends('model_id', 'record')
    def _compute_name(self):
        for record in self:
            model = self.env['ir.model'].sudo().search([('model', '=', record.model_id.model)], limit=1)
            record_id = self.env[model.model].sudo().browse(record.record)
            audit = self.env['user.audit'].sudo().search([('model_ids', '=', model.id)], limit=1)
            if audit and record_id:
                record.record_name = record_id.name

    @api.onchange('model_id', 'record')
    def _onchange_name(self):
        for record in self:
            model = self.env['ir.model'].sudo().search([('model', '=', record.model_id.model)], limit=1)
            record_id = self.env[model.model].sudo().browse(record.record)
            audit = self.env['user.audit'].sudo().search([('model_ids', '=', model.id)], limit=1)
            if audit and record_id:
                record.record_name = record_id.name

    @api.depends('model_id', 'record')
    def _compute_description(self):
        for record in self:
            model = self.env['ir.model'].sudo().search([('model', '=', record.model_id.model)], limit=1)
            record_id = self.env[model.model].sudo().browse(record.record)
            audit = self.env['user.audit'].sudo().search([('model_ids', '=', model.id)], limit=1)
            if audit and record_id:
                raw_data = record_id.read()
                try:
                    json_string = json.dumps(raw_data, default=date_utils.json_default)
                    data = json.loads(json_string)[0]
                    json_data = {}
                    for key in data.keys():
                        if key.startswith('avatar_'):
                            continue
                        elif key.startswith('image_'):
                            continue
                        elif key.endswith('_id_domain'):
                            continue
                        elif key.endswith('_ids'):
                            continue
                        elif key.endswith('_id'):
                            continue
                        json_data[key] = data[key]
                    json_string = json.dumps(json_data, default=date_utils.json_default)
                except json.JSONDecodeError as error:
                    json_string = ''
                except ValueError as error:
                    json_string = ''
                record.record_description = json_string

    @api.onchange('model_id', 'record')
    def _onchange_description(self):
        for record in self:
            model = self.env['ir.model'].sudo().search([('model', '=', record.model_id.model)], limit=1)
            record_id = self.env[model.model].sudo().browse(record.record)
            audit = self.env['user.audit'].sudo().search([('model_ids', '=', model.id)], limit=1)
            if audit and record_id:
                raw_data = record_id.read()
                try:
                    json_string = json.dumps(raw_data, default=date_utils.json_default)
                    data = json.loads(json_string)[0]
                    json_data = {}
                    for key in data.keys():
                        if key.startswith('avatar_'):
                            continue
                        elif key.startswith('image_'):
                            continue
                        elif key.endswith('_id_domain'):
                            continue
                        elif key.endswith('_ids'):
                            continue
                        elif key.endswith('_id'):
                            continue
                        json_data[key] = data[key]
                    json_string = json.dumps(json_data, default=date_utils.json_default)
                except json.JSONDecodeError as error:
                    json_string = ''
                except ValueError as error:
                    json_string = ''
                record.record_description = json_string

    @api.model_create_multi
    def create(self, values):
        """ For adding sequence number """
        vals = values[0]
        if vals.get('name', 'New'):
            vals['name'] = self.env['ir.sequence'].sudo().next_by_code(
                'user.audit.log')
        res = super(UserAuditLogs, self).create(vals)
        return res

    def action_open_filter(self):
        view_id = self.env.ref('user_audit.user_audit_filter_wizard').id
        return {
            'name': 'Filtrer les logs des utilisateurs',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'user.audit.filter.wizard',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
        }

    def action_reset_filter(self):
        self.env['ir.config_parameter'].sudo().set_param(f'siantou.filter_user_{self.env.user.id}', '')
        # action = self.env.ref('user_audit.user_audit_log_view_tree').read()[0]
        # action.update({
        #     'target': 'main',
        # })
        # return action
        tree_view = self.env.ref('user_audit.user_audit_log_view_tree').id
        return {
            'name': 'User Audit Logs',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form,kanban',
            'res_model': 'user.audit.log',
            'views': [(tree_view, 'tree'), (False, 'form'), (False, 'kanban')],
            'view_id': tree_view,
            'domain' : [],
            'target': 'main',
        }
