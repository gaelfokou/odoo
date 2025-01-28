# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, fields, models
from odoo.exceptions import AccessDenied, UserError
from odoo.addons.auth_signup.models.res_users import SignupError
import json

class ResUsers(models.Model):
    _inherit = 'res.users'

    sh_office365_refresh_token = fields.Char('Office365 Refresh Token')

    @api.model
    def _office365_generate_signup_values(self, provider, params):
        email = params.get('email')
        return {
            'name': params.get('name', email),
            'login': email,
            'groups_id': [(6,0, [self.env.ref('base.group_user').id])],
            'email': email,
            'oauth_provider_id': provider,
            'oauth_uid': params['user_id'],
            'company_id': 1,
            'oauth_access_token': params['access_token'],
            'active': True,
            'sh_office365_refresh_token': params['sh_office365_refresh_token']
        }

    @api.model
    def _office365_signin(self, provider, params):
        try:

            oauth_uid = params['user_id']
            users = self.sudo().search([
                ("oauth_uid", "=", oauth_uid),
                ('oauth_provider_id', '=', provider)
            ], limit=1)
            if not users:
                users = self.sudo().search([
                    ("login", "=", params.get('email'))
                ], limit=1)
            if not users:
                raise AccessDenied()
            assert len(users.ids) == 1
            users.sudo().write({
                'oauth_access_token': params['access_token'],
                'sh_office365_refresh_token': params['sh_office365_refresh_token']})
            return users.login
        except AccessDenied as access_denied_exception:
            if self.env.context.get('no_user_creation'):
                return None
            state = params['state']
            token = state.get('t')
            values = self._office365_generate_signup_values(provider, params)
            print("n\n\nvaluessss",values)
            try:
                login, _ = self.with_context(
                    mail_create_nosubscribe=True).signup(values, token)
                return login
            except (SignupError, UserError):
                raise access_denied_exception

    @api.model
    def office365_auth_oauth(self, provider, params):
        access_token = params.get('access_token')
        login = self._office365_signin(provider, params)
        print("n\n\nn",login)
        if not login:
            raise AccessDenied()
        return self._cr.dbname, login, access_token
