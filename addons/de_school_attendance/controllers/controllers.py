# -*- coding: utf-8 -*-
# from odoo import http


# class DeSchoolAttendance(http.Controller):
#     @http.route('/de_school_attendance/de_school_attendance', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/de_school_attendance/de_school_attendance/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('de_school_attendance.listing', {
#             'root': '/de_school_attendance/de_school_attendance',
#             'objects': http.request.env['de_school_attendance.de_school_attendance'].search([]),
#         })

#     @http.route('/de_school_attendance/de_school_attendance/objects/<model("de_school_attendance.de_school_attendance"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('de_school_attendance.object', {
#             'object': obj
#         })
