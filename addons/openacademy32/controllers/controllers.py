# -*- coding: utf-8 -*-
# from odoo import http


# class Openacademy32(http.Controller):
#     @http.route('/openacademy32/openacademy32', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/openacademy32/openacademy32/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('openacademy32.listing', {
#             'root': '/openacademy32/openacademy32',
#             'objects': http.request.env['openacademy32.openacademy32'].search([]),
#         })

#     @http.route('/openacademy32/openacademy32/objects/<model("openacademy32.openacademy32"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('openacademy32.object', {
#             'object': obj
#         })
