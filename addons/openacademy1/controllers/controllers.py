# -*- coding: utf-8 -*-
# from odoo import http


# class Openacademy1(http.Controller):
#     @http.route('/openacademy1/openacademy1', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/openacademy1/openacademy1/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('openacademy1.listing', {
#             'root': '/openacademy1/openacademy1',
#             'objects': http.request.env['openacademy1.openacademy1'].search([]),
#         })

#     @http.route('/openacademy1/openacademy1/objects/<model("openacademy1.openacademy1"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('openacademy1.object', {
#             'object': obj
#         })

