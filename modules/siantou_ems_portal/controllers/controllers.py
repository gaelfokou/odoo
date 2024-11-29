# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request, content_disposition
from odoo.addons.portal.controllers import portal
from odoo.exceptions import UserError, ValidationError
from .timetable_helpers import TimeTableHelpers  # Importer la classe helper
import logging

_logger = logging.getLogger(__name__)

class PortalAccount(portal.CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'portal_timetable' in counters:
            is_user = None
            if http.request.env.user.employee_id.id:
                is_user = 'is_teacher'
            else:
                user = http.request.env['oe.school.student'].sudo().search([('user_id', '=', http.request.env.user.id)], limit=1)
                if user:
                    is_user = 'is_student'
            values['portal_timetable'] = 1
            values['portal_schoolfee'] = 0 if is_user == 'is_teacher' else (1 if is_user == 'is_student' else 0)
        return values

    @http.route(['/my/timetable', '/my/timetable/page/<int:page>'], type='http', auth="user", website=True)
    def portal_timetable(self, page=1, search=None, search_in='all', sortby=None, **kw):
        # Utilisation de la fonction du helper
        search_timetables, searchbar_inputs, search_in, sortby, searchbar_sortings = TimeTableHelpers.timetable(search, search_in, sortby)
        return request.render('siantou_ems_portal.siantou_ems_portal_my_home_timetable_views',
                                {
                                    'timetable': search_timetables,
                                    'page_name': 'timetable',
                                    'search': search,
                                    'search_in': search_in,
                                    'searchbar_inputs': searchbar_inputs,
                                    'sortby': sortby,
                                    'searchbar_sortings': searchbar_sortings,
                                })

    @http.route(['/my/timetable/download', '/my/timetable/download/page/<int:page>'], type='http', auth="user", website=True)
    def portal_timetable_download(self, page=1, search=None, search_in='all', sortby=None, **kw):
        report_name = 'siantou_ems_core.report_timetable'
        report_action = 'siantou_ems_core.action_report_timetable'
        pdf_report = request.env['ir.actions.report'].sudo()._get_report_from_name(report_action)
        semester_ids = request.env['siantou.ems.core.year.semester'].sudo().search([])
        semester_ids = list(semester_ids)
        semester_id = semester_ids[0]
        group_ids = request.env['siantou.ems.timetable.group'].sudo().search([])
        group_ids = list(group_ids)
        group_id = group_ids[0]
        report_data = request.env['siantou.ems.timetable.timetable_print_wizard'].sudo().create({
            'semester_id': semester_id.id,
            'group_id': group_id.id,
        })
        user = None
        is_user = None
        if http.request.env.user.employee_id.id:
            user = http.request.env.user.employee_id
            is_user = 'is_teacher'
        else:
            user = http.request.env['oe.school.student'].sudo().search([('user_id', '=', http.request.env.user.id)], limit=1)
            if user:
                is_user = 'is_student'
        if user:
            data = report_data.print_timetable_report_data(user, is_user)
            pdf, _ = pdf_report.sudo().with_context()._render_qweb_pdf(report_name, data=data)
        else:
            pdf = None
        filename = 'Emploi du temps PDF.pdf'
        content_type = 'application/pdf'
        pdfhttpheaders = [
            ('Content-Type', content_type),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', content_disposition(filename)),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)

    @http.route(['/my/schoolfee', '/my/schoolfee/page/<int:page>'], type='http', auth="user", website=True)
    def portal_schoolfee(self, page=1, search=None, search_in='all', sortby=None, **kw):
        # Utilisation de la fonction du helper
        search_schoolfees, searchbar_inputs, search_in, sortby, searchbar_sortings = TimeTableHelpers.timetable(search, search_in, sortby)
        return request.render('siantou_ems_portal.siantou_ems_portal_my_home_schoolfee_views',
                                {
                                    'schoolfee': search_schoolfees,
                                    'page_name': 'schoolfee',
                                    'search': search,
                                    'search_in': search_in,
                                    'searchbar_inputs': searchbar_inputs,
                                    'sortby': sortby,
                                    'searchbar_sortings': searchbar_sortings,
                                })
