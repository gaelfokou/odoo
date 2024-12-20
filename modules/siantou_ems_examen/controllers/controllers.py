# -*- coding: utf-8 -*-
# from odoo import http


# class aftMain(http.Controller):
#     @http.route('/aft_main/aft_main', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/aft_main/aft_main/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('aft_main.listing', {
#             'root': '/aft_main/aft_main',
#             'objects': http.request.env['aft_main.aft_main'].search([]),
#         })

#     @http.route('/aft_main/aft_main/objects/<model("aft_main.aft_main"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('aft_main.object', {
#             'object': obj
#         })
