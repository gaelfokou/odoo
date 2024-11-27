# -*- coding: utf-8 -*-
from odoo import http
from odoo.addons.portal.controllers import portal
from odoo.exceptions import UserError, ValidationError
from .timetable_helpers import TimeTableHelpers  # Importer la classe helper
import logging

_logger = logging.getLogger(__name__)

class PortalAccount(portal.CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'portal_timetable' in counters:
            # user = http.request.env.user.partner_id
            user = http.request.env.user.employee_id
            count = http.request.env['siantou.ems.timetable.timetable'].sudo().search_count([('employee_id', '=', user.id)])
            values['portal_timetable'] = count if count > 0 else 1
        return values

    @http.route(['/my/timetable', '/my/timetable/page/<int:page>'], type='http', auth="user", website=True)
    def portal_timetable(self, search=None, search_in='all', sortby=None):
        # Utilisation de la fonction du helper
        search_timetables, searchbar_inputs, search_in, sortby, searchbar_sortings = TimeTableHelpers.timetable(search, search_in, sortby)
        return http.request.render('siantou_ems_portal.siantou_ems_portal_my_home_timetable_views',
                                {
                                    'timetable': search_timetables,
                                    'page_name': 'timetable',
                                    'search': search,
                                    'search_in': search_in,
                                    'searchbar_inputs': searchbar_inputs,
                                    'sortby': sortby,
                                    'searchbar_sortings': searchbar_sortings,
                                })
