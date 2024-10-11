# -*- coding: utf-8 -*-
from odoo import http


class siantou_emploidetemp(http.Controller):
    # @http.route('/siantou/emploidetemp', type='http', auth='public', website=True)
    # def index(self, **kw):
    #     return "Hello, world"

    @http.route('/siantou/emploidetemp', type='http', auth='public', website=True)
    def list(self, **kw):
        return http.request.render('siantou_emploidetemp.emploidetemp_listing', {
            'root': '/siantou/emploidetemp',
            'emploidetemps': http.request.env['siantou.emploidetemp'].search([]),
        })

    @http.route('/siantou/emploidetemp/<model("siantou.emploidetemp"):obj>', type='http', auth='public', website=True)
    def object(self, obj, **kw):
        return http.request.render('siantou_emploidetemp.emploidetemp_object', {
            'emploidetemp': obj
        })
