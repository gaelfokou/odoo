# -*- coding: utf-8 -*-
from odoo import http
from odoo.addons.portal.controllers import portal
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class PortalAccount(portal.CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'portal_timetable' in counters:
            search_domain = []

            if http.request.env.user.employee_id.id:
                user = http.request.env.user.employee_id
                search_domain.insert(0, ('employee_id', '=', user.id))
            else:
                user = http.request.env.user.partner_id

            count = http.request.env['siantou.ems.timetable.timetable'].sudo().search_count(search_domain)
            values['portal_timetable'] = count if count > 0 else 1

        return values

    @http.route(['/my/timetable', '/my/timetable/page/<int:page>'], type='http', auth="user", website=True)
    def portal_timetable(self, search=None, search_in='all', sortby=None):
        if not search:
            search = ''
        searchbar_inputs = {
            'all': {'label': 'Tout', 'input': 'all', 'domain': []},
            'filiere': {'label': 'Filière', 'input': 'filiere', 'domain': [('field_of_study_id.name', 'like', search)]},
            'cours': {'label': 'Cours', 'input': 'cours', 'domain': [('subject_id.name', 'like', search)]},
            'enseignant': {'label': 'Enseignant', 'input': 'enseignant', 'domain': [('employee_id.name', 'like', search)]},
        }
        if search_in not in searchbar_inputs.keys():
            search_in = 'all'
        search_domain = searchbar_inputs[search_in]['domain']

        searchbar_sortings = {
            'date-desc': {'label': 'Date desc', 'order': 'date desc'},
            'date-asc': {'label': 'Date asc', 'order': 'date asc'},
        }
        if not sortby or sortby not in searchbar_sortings.keys():
            sortby = 'date-desc'
        order = searchbar_sortings[sortby]['order']

        if http.request.env.user.employee_id.id:
            user = http.request.env.user.employee_id
            search_domain.insert(0, ('employee_id', '=', user.id))
        else:
            user = http.request.env.user.partner_id

        search_timetables = http.request.env['siantou.ems.timetable.timetable'].sudo().search(search_domain, order=order)

        _logger.info(f'----------- tototototototo user {user.id} -----------')
        _logger.info(f'----------- tototototototo search_timetables {search_timetables} -----------')

        return http.request.render('siantou_ems_portal.portal_my_home_timetable_views',
                                {
                                    'timetable': search_timetables,
                                    'page_name': 'timetable',
                                    'search': search,
                                    'search_in': search_in,
                                    'searchbar_inputs': searchbar_inputs,
                                    'sortby': sortby,
                                    'searchbar_sortings': searchbar_sortings,
                                })

# class CustomerPortalCustom(http.Controller):
#     @http.route('/siantou_ems_portal/siantou_ems_portal', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/siantou_ems_portal/siantou_ems_portal/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('siantou_ems_portal.listing', {
#             'root': '/siantou_ems_portal/siantou_ems_portal',
#             'objects': http.request.env['siantou_ems_portal.siantou_ems_portal'].search([]),
#         })

#     @http.route('/siantou_ems_portal/siantou_ems_portal/objects/<model("siantou_ems_portal.siantou_ems_portal"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('siantou_ems_portal.object', {
#             'object': obj
#         })

