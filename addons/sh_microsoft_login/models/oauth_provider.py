# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

import urllib
import simplejson
from odoo.http import request
from odoo import fields, models

class AuthOauthProvider(models.Model):
    _inherit = 'auth.oauth.provider'

    secret_key = fields.Char('Secret Key')
    def oauth_token(
            self, type_grant, oauth_provider_rec, code=None,
            refresh_token=None, context=None):
            
        data = dict(
            grant_type=type_grant,
            redirect_uri=(request.httprequest.host_url).rstrip("/") + '/office365_connection/microsoft',
            client_id=oauth_provider_rec.client_id,
            client_secret=oauth_provider_rec.secret_key,
        )
        if code:
            data.update({'code': code})
        elif refresh_token:
            data.update({'refresh_token': refresh_token})
        return simplejson.loads(urllib.request.urlopen(
            urllib.request.Request(
                oauth_provider_rec.validation_endpoint,
                urllib.parse.urlencode(data).encode("utf-8"))).read())
