# -*- coding: utf-8 -*-
# from odoo import http


# class Openacademy31(http.Controller):
#     @http.route('/openacademy31/openacademy31', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/openacademy31/openacademy31/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('openacademy31.listing', {
#             'root': '/openacademy31/openacademy31',
#             'objects': http.request.env['openacademy31.openacademy31'].search([]),
#         })

#     @http.route('/openacademy31/openacademy31/objects/<model("openacademy31.openacademy31"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('openacademy31.object', {
#             'object': obj
#         })
