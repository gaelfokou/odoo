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
            # user = request.env.user.partner_id
            user = request.env.user.employee_id
            count = request.env['siantou.ems.timetable.timetable'].sudo().search_count([('employee_id', '=', user.id)])
            values['portal_timetable'] = count if count > 0 else 1
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
        pdf_report = request.env['siantou.ems.timetable.timetable']
        pdf, _ = request.env.ref('siantou_ems_core.action_report_timetable').sudo()._render_qweb_pdf(pdf_report)
        filename = 'report.pdf'
        content_type = 'application/pdf'
        pdfhttpheaders = [
            ('Content-Type', content_type),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', content_disposition(filename)),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)
