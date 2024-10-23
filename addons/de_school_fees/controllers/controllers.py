# -*- coding: utf-8 -*-
# from odoo import http


# class DeSchoolFees(http.Controller):
#     @http.route('/de_school_fees/de_school_fees', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/de_school_fees/de_school_fees/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('de_school_fees.listing', {
#             'root': '/de_school_fees/de_school_fees',
#             'objects': http.request.env['de_school_fees.de_school_fees'].search([]),
#         })

#     @http.route('/de_school_fees/de_school_fees/objects/<model("de_school_fees.de_school_fees"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('de_school_fees.object', {
#             'object': obj
#         })
