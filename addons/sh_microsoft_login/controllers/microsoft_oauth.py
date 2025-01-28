# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

import logging
import jwt
import json
import odoo
import werkzeug.utils
import werkzeug.urls
from werkzeug.exceptions import BadRequest
from odoo import api, http, SUPERUSER_ID, _
from odoo import http
from odoo.http import request
from odoo import registry as registry_get
from odoo.addons.auth_oauth.controllers.main import OAuthLogin as Home
from odoo.addons.web.controllers.utils import _get_login_redirect_url
from odoo.addons.auth_oauth.controllers.main import\
    fragment_to_query_string



_logger = logging.getLogger(__name__)


class OAuthLogin(Home):

    def list_providers(self):
        try:
            providers = request.env['auth.oauth.provider'].sudo().search_read(
                [('enabled', '=', True)])
        except Exception:
            providers = []
        office365_login = request.env.ref(
            'sh_microsoft_login.office365_login')
        base_url = (request.httprequest.host_url).rstrip("/")
        for provider in providers:
            if provider.get('id') == office365_login.id:
                state = self.get_state(provider)
                return_url = base_url + '/office365_connection/microsoft'
                params = dict(
                    client_id=provider['client_id'],
                    response_type='code',
                    redirect_uri=return_url,
                    prompt='select_account',
                    scope=provider['scope'],
                    state=json.dumps(state),
                )
            else:
                return_url = base_url + '/auth_oauth/signin'
                state = self.get_state(provider)
                params = dict(
                    response_type='token',
                    client_id=provider['client_id'],
                    redirect_uri=return_url,
                    scope=provider['scope'],
                    state=json.dumps(state),
                )
            provider['auth_link'] = "%s?%s" % (provider['auth_endpoint'],
                                               werkzeug.urls.url_encode(params))
        return providers


class OAuthController(http.Controller):

    @http.route('/office365_connection/microsoft',
                type='http',
                auth='none')
    @fragment_to_query_string
    def microsoft_signin(self, **kw):
        state = json.loads(kw['state'])
        dbname = state['d']
        if not http.db_filter([dbname]):
            return BadRequest()
        provider = state['p']
        registry = registry_get(dbname)
        req = request.env
        root_url = (request.httprequest.host_url).rstrip("/") + '/'
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            provider = env.ref('sh_microsoft_login.office365_login')
            authorization_data = \
                req['auth.oauth.provider'].sudo().oauth_token(
                    'authorization_code',
                    provider,
                    kw.get('code'),
                    refresh_token=None)

            access_token = authorization_data.get('access_token')
            refresh_token = authorization_data.get('refresh_token')
            try:
                if 'https' in root_url:
                    data = jwt.decode(access_token,verify=False)
                else:
                    data = jwt.decode(access_token, options={"verify_signature": False})
                print("n\n\n\datatata",data)
                displayName = data.get('name')
                email1 = data.get('emails')
                email2 = data.get('email')
                upn = data.get('upn')
                if email1 is not None:
                    mail = email2
                elif  upn is not None:
                    mail = upn
                else:
                    mail = email1
                user_id = data.get('oid')
                print("n\n\nmail",mail)
            except Exception as e:
                _logger.info(e)
            with registry.cursor() as cr:
                try:
                    db, login, key = req['res.users'].sudo().office365_auth_oauth(
                        provider.id, {
                            'access_token': access_token,
                            'user_id': user_id,
                            'email': mail,
                            'name': displayName,
                            'sh_office365_refresh_token': refresh_token,
                            'state' : state,
                        })
                    request.cr.commit()
                    pre_uid = request.session.authenticate(db, login, key)
                    resp = request.redirect(_get_login_redirect_url(pre_uid, root_url), 303)
                    resp.autocorrect_location_header = False
                    if werkzeug.urls.url_parse(resp.location).path == '/web' and not request.env.user._is_internal():
                        resp.location = '/'
                    return resp
                except AttributeError:
                    _logger.error(
                        "auth_signup not installed on"
                        " database %s: oauth sign up cancelled." % (
                            request.cr.dbname))
                    url = "/web/login?oauth_error=1"
                except odoo.exceptions.AccessDenied:
                    _logger.info(
                        'OAuth2: access denied,'
                        ' redirect to main page in case a valid'
                        ' session exists, without setting cookies')
                    url = "/web/login?oauth_error=3"
                    redirect = werkzeug.utils.redirect(url, 303)
                    redirect.autocorrect_location_header = False
                    return redirect
                except Exception as e:
                    _logger.exception("OAuth2: %s" % str(e))
                    url = "/web/login?oauth_error=2"
                redirect = request.redirect(url, 303)
                redirect.autocorrect_location_header = False
                return redirect
