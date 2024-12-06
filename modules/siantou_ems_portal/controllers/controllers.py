# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request, content_disposition
from odoo.addons.portal.controllers import portal
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
from .helpers import Helpers
import logging

DATE_FORMAT = '%Y-%m-%d'
DATE_FORMAT_FR = '%d/%m/%Y'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATETIME_FORMAT_FR = '%d/%m/%Y %H:%M:%S'

CURRENT_WEEKDAY = {
    0: 'Lundi',
    1: 'Mardi',
    2: 'Mercredi',
    3: 'Jeudi',
    4: 'Vendredi',
    5: 'Samedi',
    6: 'Dimanche'
}

TYPE_PAIEMENT = {
    'pu': 'Paiement unique',
    'pt': 'Paiement par tranches',
}

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
            values['portal_schoolfee'] = 1 if is_user == 'is_student' else 0
            values['portal_paymenthistory'] = 1 if is_user == 'is_teacher' else 0
        return values

    @http.route(['/my/timetable', '/my/timetable/page/<int:page>'], type='http', auth="user", website=True)
    def portal_timetable(self, page=1, search=None, search_in='all', sortby=None, **kw):
        # Utilisation de la fonction du helper
        search_timetables, searchbar_inputs, search_in, sortby, searchbar_sortings = Helpers.timetable(search, search_in, sortby)
        timetables = []
        for search_timetable in search_timetables:
            timetable = {}
            timetable['date'] = date.strftime(search_timetable.date, DATE_FORMAT_FR)
            timetable['field_of_study_name'] = search_timetable.field_of_study_id.name
            timetable['semester_name'] = search_timetable.semester_id.name
            timetable['level_name'] = search_timetable.level_id.name
            timetable['subject_name'] = search_timetable.subject_id.name
            timetable['classroom_name'] = search_timetable.classroom_id.name
            timetable['employee_name'] = search_timetable.employee_id.name
            # timetable['day_of_week'] = CURRENT_WEEKDAY[search_timetable.day_of_week]
            timetable['day_of_week'] = CURRENT_WEEKDAY[search_timetable.date.weekday()]
            timetable['start_time'] = search_timetable.start_time
            timetable['end_time'] = search_timetable.end_time
            timetables.append(timetable)
        return request.render('siantou_ems_portal.siantou_ems_portal_my_home_timetable_views',
                                {
                                    'timetable': timetables,
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
        search_schoolfees, searchbar_inputs, search_in, sortby, searchbar_sortings = Helpers.schoolfee(search, search_in, sortby)
        total_amount = 0.0
        total_structure_amount = 0.0
        total_rest_amount = 0.0
        schoolfees = []
        for search_schoolfee in search_schoolfees:
            schoolfee = {}
            schoolfee['date_payment'] = date.strftime(search_schoolfee.date_payment, DATE_FORMAT_FR)
            schoolfee['name'] = search_schoolfee.name
            schoolfee['reference'] = search_schoolfee.reference
            schoolfee['structure_frais_type_paiement'] = TYPE_PAIEMENT[search_schoolfee.structure_frais_id.type_paiement]
            schoolfee['amount'] = search_schoolfee.amount
            schoolfee['structure_frais_amount_total'] = search_schoolfee.structure_frais_id.amount_total
            schoolfee['state'] = search_schoolfee.state if hasattr(search_schoolfee, 'state') else ''
            schoolfees.append(schoolfee)
            total_amount += search_schoolfee.amount
            total_structure_amount += search_schoolfee.structure_frais_id.amount_total
            total_rest_amount = total_structure_amount - total_amount
        return request.render('siantou_ems_portal.siantou_ems_portal_my_home_schoolfee_views',
                                {
                                    'schoolfee': schoolfees,
                                    'page_name': 'schoolfee',
                                    'total_amount': total_amount,
                                    'total_structure_amount': total_structure_amount,
                                    'total_rest_amount': total_rest_amount,
                                })

    @http.route(['/my/paymenthistory', '/my/paymenthistory/page/<int:page>'], type='http', auth="user", website=True)
    def portal_paymenthistory(self, page=1, search=None, search_in='all', sortby=None, **kw):
        # Utilisation de la fonction du helper
        search_paymenthistories, searchbar_inputs, search_in, sortby, searchbar_sortings = Helpers.paymenthistory(search, search_in, sortby)
        paymenthistories = []
        for search_paymenthistory in search_paymenthistories:
            paymenthistory = {}
            paymenthistory['date_from'] = date.strftime(search_paymenthistory.date_from, DATE_FORMAT_FR)
            paymenthistory['name'] = search_paymenthistory.name
            paymenthistory['number'] = search_paymenthistory.number
            paymenthistory['code'] = search_paymenthistory.code
            paymenthistory['contract'] = search_paymenthistory.contract_id.name
            if search_paymenthistory.code:
                paymenthistory['amount'] = search_paymenthistory.line_ids.filtered(lambda line: line.salary_rule_id.code == search_paymenthistory.code).mapped('amount')[0] if (len(list(search_paymenthistory.line_ids)) > 0 and len(search_paymenthistory.line_ids.filtered(lambda line: line.salary_rule_id.code == search_paymenthistory.code)) > 0) else 0.0
            else:
                paymenthistory['amount'] = search_paymenthistory.line_ids.mapped('amount')[0] if len(list(search_paymenthistory.line_ids)) > 0 else 0.0
            paymenthistory['number_of_hours'] = sum(search_paymenthistory.worked_days_line_ids.mapped('number_of_hours')) if len(list(search_paymenthistory.worked_days_line_ids)) > 0 else 0.0
            paymenthistory['state'] = search_paymenthistory.state
            paymenthistories.append(paymenthistory)
        return request.render('siantou_ems_portal.siantou_ems_portal_my_home_paymenthistory_views',
                                {
                                    'paymenthistory': paymenthistories,
                                    'page_name': 'paymenthistory',
                                })
