# -*- coding: utf-8 -*-
# from odoo import http


# class Openacademy3(http.Controller):
#     @http.route('/openacademy3/openacademy3', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/openacademy3/openacademy3/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('openacademy3.listing', {
#             'root': '/openacademy3/openacademy3',
#             'objects': http.request.env['openacademy3.openacademy3'].search([]),
#         })

#     @http.route('/openacademy3/openacademy3/objects/<model("openacademy3.openacademy3"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('openacademy3.object', {
#             'object': obj
#         })

