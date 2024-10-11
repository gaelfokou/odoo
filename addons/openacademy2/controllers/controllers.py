# -*- coding: utf-8 -*-
# from odoo import http


# class Openacademy2(http.Controller):
#     @http.route('/openacademy2/openacademy2', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/openacademy2/openacademy2/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('openacademy2.listing', {
#             'root': '/openacademy2/openacademy2',
#             'objects': http.request.env['openacademy2.openacademy2'].search([]),
#         })

#     @http.route('/openacademy2/openacademy2/objects/<model("openacademy2.openacademy2"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('openacademy2.object', {
#             'object': obj
#         })
