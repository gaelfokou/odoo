# -*- coding: utf-8 -*-
from odoo import http
from odoo.addons.portal.controllers import portal
from odoo.exceptions import UserError, ValidationError
from odoo.addons.web.controllers.home import Home as WebHome
from odoo.addons.web.controllers.utils import is_user_internal
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
from .helpers import Helpers
import logging

DATE_FORMAT = '%Y-%m-%d'
DATE_FORMAT_FR = '%d/%m/%Y'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATETIME_FORMAT_FR = '%d/%m/%Y %H:%M'
TIME_FORMAT = '%H:%M:%S'
TIME_FORMAT_FR = '%H:%M'

CURRENT_WEEKDAY = {
    0: 'Lundi',
    1: 'Mardi',
    2: 'Mercredi',
    3: 'Jeudi',
    4: 'Vendredi',
    5: 'Samedi',
    6: 'Dimanche',
}

STATUS_TIMETABLE = {
    'pending': 'En attente',
    'progress': 'En cours',
    'present': 'Présent',
    'absent': 'Absent',
    'permission': 'Permission',
    'exception': 'Exception',
}

TYPE_PAIEMENT = {
    'pu': 'Paiement unique',
    'pt': 'Paiement par tranches',
}

STATUS_NOTIFICATION = {
    'pending': 'En attente',
    'sent': 'Envoyé',
}

_logger = logging.getLogger(__name__)

class Home(WebHome):
    def _login_redirect(self, uid, redirect=None):
        if not redirect and not is_user_internal(uid):
            res_user_id = http.request.env['res.users'].sudo().search([
                ('id', '=', uid),
            ], limit=1)
            user = None
            is_user = None
            if res_user_id.employee_id.id:
                user = res_user_id.employee_id
                if res_user_id.employee_id.is_teacher:
                    is_user = 'is_teacher'
                else:
                    is_user = 'is_employee'
            else:
                user = http.request.env['oe.school.student'].sudo().search([('user_id', '=', res_user_id.id)], limit=1)
                if user:
                    is_user = 'is_student'
            if user:
                if is_user == 'is_student':
                    if not user.private_phone:
                        redirect = '/my/request'
                    if not user.private_email:
                        redirect = '/my/request'
                    if not user.date_naissance:
                        redirect = '/my/request'
                    if not user.nationalite.id:
                        redirect = '/my/request'
                    if not user.city_id.id:
                        redirect = '/my/request'
        return super()._login_redirect(uid, redirect=redirect)

class PortalAccount(portal.CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'portal_timetable' in counters:
            is_user = None
            if http.request.env.user.employee_id.id:
                if http.request.env.user.employee_id.is_teacher:
                    is_user = 'is_teacher'
                else:
                    is_user = 'is_employee'
            elif http.request.env.user.student_id.id:
                is_user = 'is_student'
            values['portal_timetable'] = 1
            values['portal_schoolfee'] = 1 if is_user == 'is_student' else 0
            values['portal_paymenthistory'] = 1 if is_user == 'is_teacher' else 0
            values['portal_accountbalance'] = 1 if is_user == 'is_teacher' else 0
            values['portal_notification'] = 1 if is_user == 'is_teacher' else 0
            values['portal_request'] = 0
        return values

    @http.route(['/my/timetable', '/my/timetable/page/<int:page>'], type='http', auth="user", website=True)
    def portal_timetable(self, page=1, search='', search_in='all', view_type='calendar', **kw):
        if view_type not in ['calendar', 'list']:
            view_type = 'calendar'
        # Utilisation de la fonction du helper
        search_timetables, searchbar_inputs = Helpers.timetable(search, search_in)
        timetables = []
        for search_timetable in search_timetables:
            timetable = {}
            timetable['id'] = search_timetable.id
            timetable['date'] = search_timetable.date
            timetable['date_of_week'] = datetime.strftime(search_timetable.date, DATE_FORMAT_FR)
            timetable['semester_name'] = search_timetable.semester_id.name
            timetable['cycle_name'] = search_timetable.cycle_id.name
            timetable['level_name'] = search_timetable.level_id.name
            timetable['field_of_study_id'] = search_timetable.field_of_study_id.id
            timetable['field_of_study_name'] = search_timetable.field_of_study_id.name
            timetable['specialty_name'] = search_timetable.specialty_id.name
            timetable['option_name'] = search_timetable.option_id.name
            timetable['class_name'] = search_timetable.class_id.name
            timetable['department_id'] = search_timetable.department_id.id
            timetable['department_name'] = search_timetable.department_id.name
            timetable['subject_name'] = search_timetable.subject_id.name
            timetable['subject_code'] = search_timetable.subject_id.code
            timetable['subject_shared_subject'] = '(TC)' if search_timetable.subject_id.shared_subject else ''
            timetable['classroom_name'] = search_timetable.classroom_id.name
            timetable['building_name'] = search_timetable.classroom_id.building_id.name
            timetable['batch_name'] = search_timetable.batch_id.name
            timetable['employee_name'] = search_timetable.employee_id.name
            timetable['day_of_week'] = CURRENT_WEEKDAY[search_timetable.date.weekday()]
            timetable['start_time'] = search_timetable.start_time
            timetable['end_time'] = search_timetable.end_time
            timetable['status'] = STATUS_TIMETABLE[search_timetable.status]
            timetables.append(timetable)
        if view_type == 'calendar':
            if len(timetables) > 0:
                field_of_study_id = timetables[0]['field_of_study_id']

                slots = http.request.env['siantou.ems.timetable.slot'].sudo().search([
                    ('is_active', '=', False),
                ])
                slots = list(slots)

                available_slotitem = None
                for slot in slots:
                    field_of_study_ids = list(slot.field_of_study_ids)
                    for field_of_study in field_of_study_ids:
                        if field_of_study.id == field_of_study_id:
                            available_slotitem = slot
                            break
                    if available_slotitem:
                        break

                if available_slotitem:
                    slots = http.request.env['siantou.ems.timetable.slot'].sudo().search([
                        ('id', '=', available_slotitem.id),
                    ])
                else:
                    slots = http.request.env['siantou.ems.timetable.slot'].sudo().search([
                        ('is_active', '=', True),
                    ])

                slots = list(slots)

                not_active_slotitems = []
                for slot in slots:
                    not_active_slotitem_day_ids = slot.slotitem_day_ids.filtered(lambda s: not s.is_active)
                    not_active_slotitem_day_ids = list(not_active_slotitem_day_ids)
                    for not_active_slotitem_day_id in not_active_slotitem_day_ids:
                        not_active_slotitems.append([round(not_active_slotitem_day_id.start_time, 2), round(not_active_slotitem_day_id.end_time, 2)])
                    not_active_slotitem_night_ids = slot.slotitem_night_ids.filtered(lambda s: not s.is_active)
                    not_active_slotitem_night_ids = list(not_active_slotitem_night_ids)
                    for not_active_slotitem_night_id in not_active_slotitem_night_ids:
                        not_active_slotitems.append([round(not_active_slotitem_night_id.start_time, 2), round(not_active_slotitem_night_id.end_time, 2)])

                timetables = Helpers.format_timetable(timetables, not_active_slotitems)
            else:
                timetables = Helpers.format_timetable(timetables)
            for monday in timetables.keys():
                for i, timetable in enumerate(timetables[monday]['Heure']):
                    tm = timetable.split('-')
                    tm[0] = Helpers.convert_float_to_time(tm[0])
                    tm[1] = Helpers.convert_float_to_time(tm[1])
                    timetables[monday]['Heure'][i] = '{}-{}'.format(tm[0], tm[1])
            timetables = Helpers.paginate_calendar(timetables, 1, page)
        else:
            for timetable in timetables:
                timetable['date'] = date.strftime(timetable['date'], DATE_FORMAT_FR)
                timetable['start_time'] = Helpers.convert_float_to_time(timetable['start_time'])
                timetable['end_time'] = Helpers.convert_float_to_time(timetable['end_time'])
            timetables = Helpers.paginate_list(timetables, 10, page)
        return http.request.render(f'siantou_ems_portal.siantou_ems_portal_my_home_timetable_{view_type}_views',
                                {
                                    'timetables': timetables['pages'],
                                    'timetable_pages_total': timetables['pages_total'],
                                    'timetable_page_number': page,
                                    'timetable_view_type': view_type,
                                    'page_name': 'timetable',
                                    'search': search,
                                    'search_in': search_in,
                                    'searchbar_inputs': searchbar_inputs,
                                })

    @http.route(['/my/timetable/download', '/my/timetable/download/page/<int:page>'], type='http', auth="user", website=True)
    def portal_timetable_download(self, page=1, search='', search_in='all', **kw):
        user = None
        is_user = None
        if http.request.env.user.employee_id.id:
            user = http.request.env.user.employee_id
            if http.request.env.user.employee_id.is_teacher:
                is_user = 'is_teacher'
            else:
                is_user = 'is_employee'
        elif http.request.env.user.student_id.id:
            user = http.request.env.user.student_id
            is_user = 'is_student'
        if user:
            report_name = 'siantou_ems_core.report_timetable'
            report_action = 'siantou_ems_core.action_report_timetable'
            pdf_report = http.request.env['ir.actions.report'].sudo()._get_report_from_name(report_action)
            domain = []
            if is_user == 'is_teacher':
                domain.append(('employee_id', '=', user.id))
            elif is_user == 'is_student':
                domain.append(('class_id', '=', user.class_id.id))
            timetable_ids = http.request.env['siantou.ems.timetable.timetable'].sudo().search(domain, order='date asc')
            timetable_ids = list(timetable_ids)
            if len(timetable_ids) > 0:
                n = len(timetable_ids)
                timetable_id = timetable_ids[n - 1]
                report_data = http.request.env['siantou.ems.timetable.timetable_print_wizard'].sudo().create({
                    'semester_id': timetable_id.semester_id.id,
                    'group_id': timetable_id.group_id.id,
                })
                data = report_data.print_timetable_report_data(domain)
                pdf, _ = pdf_report.sudo().with_context()._render_qweb_pdf(report_name, data=data)
            else:
                pdf = None
        else:
            pdf = None
        filename = 'Emploi du temps PDF.pdf'
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', http.content_disposition(filename)),
        ]
        return http.request.make_response(
            pdf,
            headers=headers,
            status=200
        )

    @http.route(['/my/schoolfee', '/my/schoolfee/page/<int:page>'], type='http', auth="user", website=True)
    def portal_schoolfee(self, page=1, search='', search_in='all', **kw):
        # Utilisation de la fonction du helper
        search_schoolfees, searchbar_inputs = Helpers.schoolfee(search, search_in)
        total_amount = 0.0
        total_structure_amount = 0.0
        total_rest_amount = 0.0
        schoolfees = []
        for search_schoolfee in search_schoolfees:
            schoolfee = {}
            schoolfee['date_payment'] = datetime.strftime(search_schoolfee.date_payment, DATE_FORMAT_FR)
            schoolfee['name'] = search_schoolfee.name
            schoolfee['reference'] = search_schoolfee.reference
            schoolfee['structure_frais_type_paiement'] = TYPE_PAIEMENT[search_schoolfee.structure_frais_id.type_paiement]
            schoolfee['structure_frais_name'] = search_schoolfee.structure_frais_id.fee_structure_name
            schoolfee['amount'] = search_schoolfee.amount
            schoolfee['structure_frais_amount_total'] = search_schoolfee.structure_frais_id.amount_total
            schoolfee['state'] = search_schoolfee.state if hasattr(search_schoolfee, 'state') else ''
            schoolfees.append(schoolfee)
            total_amount += schoolfee['amount']
            total_structure_amount += schoolfee['structure_frais_amount_total']
            total_rest_amount = total_structure_amount - total_amount
        return http.request.render('siantou_ems_portal.siantou_ems_portal_my_home_schoolfee_views',
                                {
                                    'schoolfees': schoolfees,
                                    'page_name': 'schoolfee',
                                    'total_amount': total_amount,
                                    'total_structure_amount': total_structure_amount,
                                    'total_rest_amount': total_rest_amount,
                                })

    @http.route(['/my/paymenthistory', '/my/paymenthistory/page/<int:page>'], type='http', auth="user", website=True)
    def portal_paymenthistory(self, page=1, search='', search_in='all', **kw):
        # Utilisation de la fonction du helper
        search_paymenthistories, searchbar_inputs = Helpers.paymenthistory(search, search_in)
        total_amount = 0.0
        total_number_of_hours = 0.0
        paymenthistories = []
        for search_paymenthistory in search_paymenthistories:
            paymenthistory = {}
            paymenthistory['date_from'] = datetime.strftime(search_paymenthistory.date_from, DATE_FORMAT_FR)
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
            total_amount += paymenthistory['amount']
            total_number_of_hours += paymenthistory['number_of_hours']
        return http.request.render('siantou_ems_portal.siantou_ems_portal_my_home_paymenthistory_views',
                                {
                                    'paymenthistories': paymenthistories,
                                    'page_name': 'paymenthistory',
                                    'total_amount': total_amount,
                                    'total_number_of_hours': total_number_of_hours,
                                })

    @http.route(['/my/accountbalance', '/my/accountbalance/page/<int:page>'], type='http', auth="user", website=True)
    def portal_accountbalance(self, page=1, search='', search_in='all', **kw):
        # Utilisation de la fonction du helper
        search_accountbalances, searchbar_inputs = Helpers.paymenthistory(search, search_in)
        total_amount = 0.0
        total_number_of_hours = 0.0
        accountbalances = []
        for search_accountbalance in search_accountbalances:
            accountbalance = {}
            accountbalance['date_from'] = datetime.strftime(search_accountbalance.date_from, DATE_FORMAT_FR)
            accountbalance['name'] = search_accountbalance.name
            accountbalance['number'] = search_accountbalance.number
            accountbalance['code'] = search_accountbalance.code
            accountbalance['contract'] = search_accountbalance.contract_id.name
            if search_accountbalance.code:
                accountbalance['amount'] = search_accountbalance.line_ids.filtered(lambda line: line.salary_rule_id.code == search_accountbalance.code).mapped('amount')[0] if (len(list(search_accountbalance.line_ids)) > 0 and len(search_accountbalance.line_ids.filtered(lambda line: line.salary_rule_id.code == search_accountbalance.code)) > 0) else 0.0
            else:
                accountbalance['amount'] = search_accountbalance.line_ids.mapped('amount')[0] if len(list(search_accountbalance.line_ids)) > 0 else 0.0
            accountbalance['number_of_hours'] = sum(search_accountbalance.worked_days_line_ids.mapped('number_of_hours')) if len(list(search_accountbalance.worked_days_line_ids)) > 0 else 0.0
            accountbalance['state'] = search_accountbalance.state
            accountbalances.append(accountbalance)
            total_amount += accountbalance['amount']
            total_number_of_hours += accountbalance['number_of_hours']
        return http.request.render('siantou_ems_portal.siantou_ems_portal_my_home_accountbalance_views',
                                {
                                    'accountbalances': accountbalances,
                                    'page_name': 'accountbalance',
                                    'total_amount': total_amount,
                                    'total_number_of_hours': total_number_of_hours,
                                })

    @http.route(['/my/notification', '/my/notification/page/<int:page>'], type='http', auth="user", website=True)
    def portal_notification(self, page=1, search='', search_in='all', **kw):
        # Utilisation de la fonction du helper
        search_notifications, searchbar_inputs = Helpers.notification(search, search_in)
        notifications = []
        for search_notification in search_notifications:
            notification = {}
            notification['date'] = datetime.strftime(search_notification.date, DATE_FORMAT_FR)
            notification['name'] = search_notification.employee_id.name
            if search_notification.template == 'om_hr_payroll.om_hr_payroll_template_timetable_notification_absence':
                notification['subject_name'] = search_notification.timetable_id.subject_id.name
                notification['subject_code'] = search_notification.timetable_id.subject_id.code
                notification['classroom_name'] = search_notification.timetable_id.classroom_id.name
                notification['building_name'] = search_notification.timetable_id.classroom_id.building_id.name
            else:
                notification['subject_name'] = ''
                notification['subject_code'] = ''
                notification['classroom_name'] = ''
                notification['building_name'] = ''
            notification['template'] = search_notification.template
            notification['message'] = search_notification.message
            notification['status'] = STATUS_NOTIFICATION[search_notification.status]
            notifications.append(notification)
        return http.request.render('siantou_ems_portal.siantou_ems_portal_my_home_notification_views',
                                {
                                    'notifications': notifications,
                                    'page_name': 'notification',
                                })

    @http.route(['/my/request'], type='http', auth="user", website=True)
    def portal_request(self, **kw):
        all_countries = []
        countries = http.request.env['siantou.ems.core.country'].sudo().search([])
        for country in countries:
            all_countries.append({
                'id': country.id,
                'code': country.code,
                'name': country.name,
            })
        all_cities = []
        cities = http.request.env['siantou.ems.core.city'].sudo().search([])
        for city in cities:
            all_cities.append({
                'id': city.id,
                'name': city.name,
            })
        all_quarters = []
        quarters = http.request.env['siantou.ems.core.quarter'].sudo().search([])
        for quarter in quarters:
            all_quarters.append({
                'id': quarter.id,
                'name': quarter.name,
            })
        private_phone = None
        private_email = None
        date_naissance = None
        nationalite = None
        city_id = None
        quarter_id = None
        user = None
        is_user = None
        if http.request.env.user.employee_id.id:
            user = http.request.env.user.employee_id
        elif http.request.env.user.student_id.id:
            user = http.request.env.user.student_id
        if user:
            private_phone = user.private_phone
            private_email = user.private_email
            date_naissance = user.date_naissance
            nationalite = user.nationalite.id
            city_id = user.city_id.id
            quarter_id = user.quarter_id.id
        return http.request.render('siantou_ems_portal.siantou_ems_portal_my_home_request_views',
                                {
                                    'phone': private_phone,
                                    'email': private_email,
                                    'birthday': date_naissance,
                                    'all_countries': all_countries,
                                    'country': nationalite,
                                    'all_cities': all_cities,
                                    'city': city_id,
                                    'all_quarters': all_quarters,
                                    'quarter': quarter_id,
                                    'page_name': 'request',
                                })

    @http.route(['/my/request/submit'], type='http', auth="user", website=True, methods=['POST'])
    def portal_request_submit(self, **kw):
        user = None
        is_user = None
        if http.request.env.user.employee_id.id:
            user = http.request.env.user.employee_id
            if http.request.env.user.employee_id.is_teacher:
                is_user = 'is_teacher'
            else:
                is_user = 'is_employee'
        elif http.request.env.user.student_id.id:
            user = http.request.env.user.student_id
            is_user = 'is_student'
        if user:
            if is_user == 'is_student':
                if not kw.get('phone'):
                    return http.request.redirect('/my/request')
                if not kw.get('email'):
                    return http.request.redirect('/my/request')
                if not kw.get('birthday'):
                    return http.request.redirect('/my/request')
                if not kw.get('country'):
                    return http.request.redirect('/my/request')
                if not kw.get('city'):
                    return http.request.redirect('/my/request')
                vals = {
                    'private_phone': kw.get('phone'),
                    'private_email': kw.get('email'),
                    'date_naissance': kw.get('birthday'),
                    'nationalite': int(kw.get('country')),
                    'city_id': int(kw.get('city')),
                }
                if kw.get('quarter') and kw.get('quarter') != '':
                    vals['quarter_id'] = int(kw.get('quarter'))
                user.sudo().write(vals)
        return http.request.redirect('/my')
