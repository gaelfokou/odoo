# -*- coding: utf-8 -*-
# from odoo import http


# class SiantouEmsHr(http.Controller):
#     @http.route('/siantou_ems_hr/siantou_ems_hr', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/siantou_ems_hr/siantou_ems_hr/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('siantou_ems_hr.listing', {
#             'root': '/siantou_ems_hr/siantou_ems_hr',
#             'objects': http.request.env['siantou_ems_hr.siantou_ems_hr'].search([]),
#         })

#     @http.route('/siantou_ems_hr/siantou_ems_hr/objects/<model("siantou_ems_hr.siantou_ems_hr"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('siantou_ems_hr.object', {
#             'object': obj
#         })

