# -*- coding: utf-8 -*-
from odoo import http
import json

class siantou_emploidetemp(http.Controller):
    # @http.route('/siantou_emploidetemp/emploidetemp', auth='public', type='http')
    # def index(self, **kw):
    #     return "Hello, world"

    @http.route('/siantou_emploidetemp/emploidetemp', auth='public', type='http')
    def list(self, **kw):
        return http.request.render('siantou_emploidetemp.emploidetemp_listing', {
            'root': '/siantou_emploidetemp/emploidetemp',
            'emploidetemps': http.request.env['siantou_emploidetemp.emploidetemp'].search([]),
        })

    @http.route('/siantou_emploidetemp/emploidetemp/<model("siantou_emploidetemp.emploidetemp"):obj>', auth='public', type='http')
    def object(self, obj, **kw):
        return http.request.render('siantou_emploidetemp.emploidetemp_object', {
            'emploidetemp': obj
        })

    @http.route('/siantou_emploidetemp/semestre/<int:id>', auth='public', type='http', method=['GET'])
    def generate(self, **kw):
        return http.request.render('siantou_emploidetemp.semestre_listing', {
            'semestre': id
        })
