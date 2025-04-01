# -*- coding: utf-8 -*-
# from odoo import http

# class aftMain(http.Controller):
#     @http.route('/siantou_main/siantou_main', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/siantou_main/siantou_main/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('siantou_main.listing', {
#             'root': '/siantou_main/siantou_main',
#             'objects': http.request.env['siantou_main.siantou_main'].search([]),
#         })

#     @http.route('/siantou_main/siantou_main/objects/<model("siantou_main.siantou_main"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('siantou_main.object', {
#             'object': obj
#         })
