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
    '0': 'Lundi',
    '1': 'Mardi',
    '2': 'Mercredi',
    '3': 'Jeudi',
    '4': 'Vendredi',
    '5': 'Samedi',
    '6': 'Dimanche'
}

STATUS_TIMETABLE = {
    'pending': 'En attente',
    'progress': 'En cours',
    'present': 'Présent',
    'absent': 'Absent',
    'permission': 'Permission',
    'exception': 'Exception',
    'delay': 'Retard',
}

TYPE_PAIEMENT = {
    'pu': 'Paiement unique',
    'pt': 'Paiement par tranches',
}

STATUS_NOTIFICATION = {
    'pending': 'En attente',
    'sent': 'Envoyé',
}

STATUS_PAYMENT = {
    'draft': 'Draft',
    'verify': 'Waiting',
    'done': 'Done',
    'cancel': 'Rejected',
}

TYPE_EXAMSCORE = {
    'cc': 'Contrôle continu',
    'sn': 'Session normale',
    'rcc': 'Rattrapage contrôle continu',
    'rsn': 'Rattrapage session normale',
}

STATUS_EXAMSCORE = {
    'start': 'Début',
    'start_write': 'Début saisie',
    'end_write': 'Fin saisie',
    'end': 'Fin',
}

_logger = logging.getLogger(__name__)

class Extension(portal.CustomerPortal):
    def check_completed_request(self):
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
        if is_user:
            if is_user == 'is_student':
                if not user.private_phone:
                    return False
                if not user.private_email:
                    return False
                if not user.date_naissance:
                    return False
                if not user.nationalite.id:
                    return False
                if not user.city_id.id:
                    return False
        return True

    @http.route(['/my', '/my/home'], type='http', auth="user", website=True)
    def home(self, **kw):
        completed_request = self.check_completed_request()
        if not completed_request:
            return http.request.redirect('/my/requireddata')
        return super(Extension, self).home(**kw)

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
                is_user = 'is_student'
            if is_user:
                if is_user == 'is_student':
                    if not user.private_phone:
                        redirect = '/my/requireddata'
                    if not user.private_email:
                        redirect = '/my/requireddata'
                    if not user.date_naissance:
                        redirect = '/my/requireddata'
                    if not user.nationalite.id:
                        redirect = '/my/requireddata'
                    if not user.city_id.id:
                        redirect = '/my/requireddata'
        return super()._login_redirect(uid, redirect=redirect)

class PortalAccount(portal.CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        is_user = None
        if http.request.env.user.employee_id.id:
            if http.request.env.user.employee_id.is_teacher:
                is_user = 'is_teacher'
            else:
                is_user = 'is_employee'
        elif http.request.env.user.student_id.id:
            is_user = 'is_student'
        if 'portal_timetable' in counters:
            values['portal_timetable'] = 1
        if 'portal_schoolfee' in counters:
            values['portal_schoolfee'] = 1 if is_user == 'is_student' else 0
        if 'portal_paymenthistory' in counters:
            values['portal_paymenthistory'] = 1 if is_user == 'is_teacher' else 0
        if 'portal_accountbalance' in counters:
            values['portal_accountbalance'] = 1 if is_user == 'is_teacher' else 0
        if 'portal_consumptionhour' in counters:
            values['portal_consumptionhour'] = 1
        if 'portal_progressreport' in counters:
            values['portal_progressreport'] = 1
        if 'portal_subjectsession_list' in counters:
            values['portal_subjectsession_list'] = 0
        if 'portal_subjectsession_new' in counters:
            values['portal_subjectsession_new'] = 0
        if 'portal_subjectsession_edit' in counters:
            values['portal_subjectsession_edit'] = 0
        if 'portal_calendar' in counters:
            values['portal_calendar'] = 1
        if 'portal_notification' in counters:
            values['portal_notification'] = 1 if is_user == 'is_teacher' else 0
        if 'portal_requireddata' in counters:
            values['portal_requireddata'] = 0
        if 'portal_examscore' in counters:
            values['portal_examscore'] = 1 if is_user == 'is_student' else 0
        if 'portal_subjectscore_list' in counters:
            values['portal_subjectscore_list'] = 1 if is_user == 'is_student' else 0
        return values

    @http.route(['/my/timetable', '/my/timetable/page/<int:page>'], type='http', auth="user", website=True)
    def portal_timetable(self, page=1, search='', search_in='all', view_type='calendar', selected_month='0', **kw):
        if view_type not in ['calendar', 'list']:
            view_type = 'calendar'
        selected_month_total = [str(i) for i in range(6)]
        if selected_month not in selected_month_total:
            selected_month = '0'
        if selected_month == selected_month_total[-1]:
            timetable_selected_month = 0
        else:
            timetable_selected_month = int(selected_month) + 1
        # Utilisation de la fonction du helper
        search_timetables, searchbar_inputs, search_month = Helpers.timetable(search, search_in, selected_month)
        timetables = []
        for search_timetable in search_timetables:
            timetable = {}
            timetable['id'] = search_timetable.id
            timetable['name'] = search_timetable.name
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
            timetable['subject_hours_credit'] = search_timetable.subject_id.hours_credit
            timetable['subject_shared_subject'] = '(TC)' if search_timetable.subject_id.shared_subject else ''
            timetable['classroom_name'] = search_timetable.classroom_id.name
            timetable['building_name'] = search_timetable.classroom_id.building_id.name
            timetable['batch_name'] = search_timetable.batch_id.name
            timetable['employee_name'] = search_timetable.employee_id.name
            timetable['day_of_week'] = CURRENT_WEEKDAY[search_timetable.day_of_week]
            timetable['start_time'] = search_timetable.start_time
            timetable['end_time'] = search_timetable.end_time
            timetable['worked_start_time'] = search_timetable.worked_start_time
            timetable['worked_end_time'] = search_timetable.worked_end_time
            timetable['reason'] = search_timetable.reason
            timetable['not_active_slotitems'] = search_timetable.not_active_slotitems
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
                timetable['worked_start_time'] = Helpers.convert_float_to_time(timetable['worked_start_time'])
                timetable['worked_end_time'] = Helpers.convert_float_to_time(timetable['worked_end_time'])
            timetables = Helpers.paginate_list(timetables, 10, page)
        return http.request.render(f'siantou_ems_portal.siantou_ems_portal_timetable_{view_type}_views',
                                {
                                    'timetables': timetables['pages'],
                                    'timetable_pages_total': timetables['pages_total'],
                                    'timetable_page_number': page,
                                    'timetable_view_type': view_type,
                                    'page_name': 'timetable',
                                    'timetable': 0,
                                    'search': search,
                                    'search_in': search_in,
                                    'searchbar_inputs': searchbar_inputs,
                                    'timetable_selected_month': timetable_selected_month,
                                    'selected_month': selected_month,
                                })

    @http.route(['/my/timetable/download', '/my/timetable/download/page/<int:page>'], type='http', auth="user", website=True)
    def portal_timetable_download(self, page=1, search='', search_in='all', view_type='calendar', selected_month='0', **kw):
        if view_type not in ['calendar', 'list']:
            view_type = 'calendar'
        selected_month_total = [str(i) for i in range(6)]
        if selected_month not in selected_month_total:
            selected_month = '0'
        if selected_month == selected_month_total[-1]:
            timetable_selected_month = 0
        else:
            timetable_selected_month = int(selected_month) + 1
        # Utilisation de la fonction du helper
        search_timetables, searchbar_inputs, search_month = Helpers.timetable(search, search_in, selected_month)
        timetables = []
        for search_timetable in search_timetables:
            timetable = {}
            timetable['id'] = search_timetable.id
            timetable['name'] = search_timetable.name
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
            timetable['subject_hours_credit'] = search_timetable.subject_id.hours_credit
            timetable['subject_shared_subject'] = '(TC)' if search_timetable.subject_id.shared_subject else ''
            timetable['classroom_name'] = search_timetable.classroom_id.name
            timetable['building_name'] = search_timetable.classroom_id.building_id.name
            timetable['batch_name'] = search_timetable.batch_id.name
            timetable['employee_name'] = search_timetable.employee_id.name
            timetable['day_of_week'] = CURRENT_WEEKDAY[search_timetable.day_of_week]
            timetable['start_time'] = search_timetable.start_time
            timetable['end_time'] = search_timetable.end_time
            timetable['worked_start_time'] = search_timetable.worked_start_time
            timetable['worked_end_time'] = search_timetable.worked_end_time
            timetable['reason'] = search_timetable.reason
            timetable['not_active_slotitems'] = search_timetable.not_active_slotitems
            timetable['status'] = STATUS_TIMETABLE[search_timetable.status]
            timetables.append(timetable)
        timetable_ids = []
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
            for monday in timetables['pages'].keys():
                for hour in range(len(timetables['pages'][monday]['Heure'])):
                    for timetable in timetables['pages'][monday]['Lundi'][hour]:
                        timetable_ids.append(timetable['id'])
                    for timetable in timetables['pages'][monday]['Mardi'][hour]:
                        timetable_ids.append(timetable['id'])
                    for timetable in timetables['pages'][monday]['Mercredi'][hour]:
                        timetable_ids.append(timetable['id'])
                    for timetable in timetables['pages'][monday]['Jeudi'][hour]:
                        timetable_ids.append(timetable['id'])
                    for timetable in timetables['pages'][monday]['Vendredi'][hour]:
                        timetable_ids.append(timetable['id'])
                    for timetable in timetables['pages'][monday]['Samedi'][hour]:
                        timetable_ids.append(timetable['id'])
                    for timetable in timetables['pages'][monday]['Dimanche'][hour]:
                        timetable_ids.append(timetable['id'])
        else:
            for timetable in timetables:
                timetable['date'] = date.strftime(timetable['date'], DATE_FORMAT_FR)
                timetable['start_time'] = Helpers.convert_float_to_time(timetable['start_time'])
                timetable['end_time'] = Helpers.convert_float_to_time(timetable['end_time'])
                timetable['worked_start_time'] = Helpers.convert_float_to_time(timetable['worked_start_time'])
                timetable['worked_end_time'] = Helpers.convert_float_to_time(timetable['worked_end_time'])
            timetables = Helpers.paginate_list(timetables, 10, page)
            for timetable in timetables['pages']:
                timetable_ids.append(timetable['id'])
        timetable_ids = list(set(timetable_ids))
        domain = [
            '|',
            '&',
            ('is_active', '=', True),
            ('is_submit', '=', False),
            '&',
            ('group_parent_id.is_active', '=', True),
            ('group_parent_id.is_submit', '=', False),
        ]
        group_id = http.request.env['siantou.ems.timetable.group'].sudo().search(domain, limit=1)
        if group_id:
            report_name = 'siantou_ems_core.template_report_timetable'
            report_action = 'siantou_ems_core.action_report_timetable'
            pdf_report = http.request.env['ir.actions.report'].sudo()._get_report_from_name(report_action)
            report_data = http.request.env['timetable.print.wizard'].sudo().create({
                'group_id': group_id.id,
            })
            domain = [
                ('id', 'in', timetable_ids)
            ]
            data = report_data.print_timetable_report_data(domains=domain)
            pdf, _ = pdf_report.sudo().with_context()._render_qweb_pdf(report_name, data=data)
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

    @http.route(['/my/schoolfee'], type='http', auth="user", website=True)
    def portal_schoolfee(self, search='', search_in='all', **kw):
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
        return http.request.render('siantou_ems_portal.siantou_ems_portal_schoolfee_views',
                                {
                                    'schoolfees': schoolfees,
                                    'page_name': 'schoolfee',
                                    'schoolfee': 0,
                                    'total_amount': total_amount,
                                    'total_structure_amount': total_structure_amount,
                                    'total_rest_amount': total_rest_amount,
                                })

    @http.route(['/my/examscore'], type='http', auth="user", website=True)
    def portal_examscore(self, search='', search_in='all', **kw):
        # Utilisation de la fonction du helper
        search_examscores, searchbar_inputs = Helpers.examscore(search, search_in)
        examscores = []
        if http.request.env.user.student_id.id:
            user = http.request.env.user.student_id
            for search_examscore in search_examscores:
                examscore = {}
                examscore['id'] = search_examscore.id
                examscore['name'] = search_examscore.name
                examscore['semester_id'] = search_examscore.semester_id.id
                examscore['semester_name'] = search_examscore.semester_id.name
                examscore['class_id'] = search_examscore.class_id.id
                examscore['class_name'] = search_examscore.class_id.name
                examscore['subject_id'] = search_examscore.subject_id.id
                examscore['subject_name'] = search_examscore.subject_id.name
                examscore['subject_code'] = search_examscore.subject_id.code
                examscore['exam_type'] = TYPE_EXAMSCORE[search_examscore.exam_type]
                examscore['status'] = STATUS_EXAMSCORE[search_examscore.status]
                score_ids = search_examscore.score_ids
                score_ids = list(score_ids)
                students = []
                for score_id in score_ids:
                    student = {}
                    student['id'] = score_id.student_id.id
                    student['name'] = score_id.student_id.name
                    if score_id.exam_type == 'cc':
                        student['cc_note'] = score_id.note
                        student['sn_note'] = None
                        student['rcc_note'] = None
                        student['rsn_note'] = None
                    elif score_id.exam_type == 'sn':
                        student['cc_note'] = None
                        student['sn_note'] = score_id.note
                        student['rcc_note'] = None
                        student['rsn_note'] = None
                    elif score_id.exam_type == 'rcc':
                        student['cc_note'] = None
                        student['sn_note'] = None
                        student['rcc_note'] = score_id.note
                        student['rsn_note'] = None
                    elif score_id.exam_type == 'rsn':
                        student['cc_note'] = None
                        student['sn_note'] = None
                        student['rcc_note'] = None
                        student['rsn_note'] = score_id.note
                    students.append(student)
                examscore['students'] = students
                examscores.append(examscore)
        examscores = []
        for examscore in examscores:
            examscore = {}
            for student in examscore['students']:
                if student['id'] == user.id:
                    examscore['id'] = examscore['id']
                    examscore['name'] = examscore['name']
                    examscore['semester_id'] = examscore['semester_id']
                    examscore['semester_name'] = examscore['semester_name']
                    examscore['class_id'] = examscore['class_id']
                    examscore['class_name'] = examscore['class_name']
                    examscore['subject_id'] = examscore['subject_id']
                    examscore['subject_name'] = examscore['subject_name']
                    examscore['subject_code'] = examscore['subject_code']
                    examscore['exam_type'] = examscore['exam_type']
                    examscore['student_id'] = student['id']
                    examscore['student_name'] = student['name']
                    examscore['cc_note'] = student['cc_note']
                    examscore['sn_note'] = student['sn_note']
                    examscore['rcc_note'] = student['rcc_note']
                    examscore['rsn_note'] = student['rsn_note']
                    examscores.append(examscore)
        examscores = Helpers.format_examscore(examscores)
        all_examscores = {}
        for key_class in examscores.keys():
            for key_semester in examscores[key_class]['data'].keys():
                for key_student in examscores[key_class]['data'][key_semester]['data'].keys():
                    for key_subject in examscores[key_class]['data'][key_semester]['data'][key_student]['data'].keys():
                        for d in examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data']:
                            if key_class not in all_examscores:
                                all_examscores[key_class] = {}
                                all_examscores[key_class]['name'] = d['class_name']
                                all_examscores[key_class]['data'] = {}
                                all_examscores[key_class]['data'][key_semester] = {}
                                all_examscores[key_class]['data'][key_semester]['name'] = d['semester_name']
                                all_examscores[key_class]['data'][key_semester]['data'] = {}
                                all_examscores[key_class]['data'][key_semester]['data'][key_student] = {}
                                all_examscores[key_class]['data'][key_semester]['data'][key_student]['name'] = d['student_name']
                                all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'] = {}
                                all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject] = {}
                                all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['name'] = d['subject_name']
                                all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data'] = d
                            else:
                                if key_semester not in all_examscores[key_class]['data']:
                                    all_examscores[key_class]['data'][key_semester] = {}
                                    all_examscores[key_class]['data'][key_semester]['name'] = d['semester_name']
                                    all_examscores[key_class]['data'][key_semester]['data'] = {}
                                    all_examscores[key_class]['data'][key_semester]['data'][key_student] = {}
                                    all_examscores[key_class]['data'][key_semester]['data'][key_student]['name'] = d['student_name']
                                    all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'] = {}
                                    all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject] = {}
                                    all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['name'] = d['subject_name']
                                    all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data'] = d
                                else:
                                    if key_student not in all_examscores[key_class]['data'][key_semester]['data']:
                                        all_examscores[key_class]['data'][key_semester]['data'][key_student] = {}
                                        all_examscores[key_class]['data'][key_semester]['data'][key_student]['name'] = d['student_name']
                                        all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'] = {}
                                        all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject] = {}
                                        all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['name'] = d['subject_name']
                                        all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data'] = d
                                    else:
                                        if key_subject not in all_examscores[key_class]['data'][key_semester]['data'][key_student]['data']:
                                            all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject] = {}
                                            all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['name'] = d['subject_name']
                                            all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data'] = d
                                        else:
                                            if all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data']['exam_type'] == 'cc':
                                                if d['exam_type'] == 'sn':
                                                    all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data']['sn_note'] = d['sn_note']
                                                elif d['exam_type'] == 'rcc':
                                                    all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data']['rcc_note'] = d['rcc_note']
                                                elif d['exam_type'] == 'rsn':
                                                    all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data']['rsn_note'] = d['rsn_note']
                                            elif all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data']['exam_type'] == 'sn':
                                                if d['exam_type'] == 'cc':
                                                    all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data']['cc_note'] = d['cc_note']
                                                elif d['exam_type'] == 'rcc':
                                                    all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data']['rcc_note'] = d['rcc_note']
                                                elif d['exam_type'] == 'rsn':
                                                    all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data']['rsn_note'] = d['rsn_note']
                                            elif all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data']['exam_type'] == 'rcc':
                                                if d['exam_type'] == 'cc':
                                                    all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data']['cc_note'] = d['cc_note']
                                                elif d['exam_type'] == 'sn':
                                                    all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data']['sn_note'] = d['sn_note']
                                                elif d['exam_type'] == 'rsn':
                                                    all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data']['rsn_note'] = d['rsn_note']
                                            elif all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data']['exam_type'] == 'rsn':
                                                if d['exam_type'] == 'cc':
                                                    all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data']['cc_note'] = d['cc_note']
                                                elif d['exam_type'] == 'sn':
                                                    all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data']['sn_note'] = d['sn_note']
                                                elif d['exam_type'] == 'rcc':
                                                    all_examscores[key_class]['data'][key_semester]['data'][key_student]['data'][key_subject]['data']['rcc_note'] = d['rcc_note']
        return http.request.render('siantou_ems_portal.siantou_ems_portal_examscore_views',
                                {
                                    'examscores': all_examscores,
                                    'page_name': 'examscore',
                                    'examscore': 0,
                                })

    @http.route(['/my/paymenthistory'], type='http', auth="user", website=True)
    def portal_paymenthistory(self, search='', search_in='all', **kw):
        # Utilisation de la fonction du helper
        search_paymenthistories, searchbar_inputs = Helpers.paymenthistory(search, search_in)
        total_amount = 0.0
        total_number_of_hours = 0.0
        paymenthistories = []
        for search_paymenthistory in search_paymenthistories:
            paymenthistory = {}
            paymenthistory['date'] = '{} - {}'.format(datetime.strftime(search_paymenthistory.date_from, DATE_FORMAT_FR), datetime.strftime(search_paymenthistory.date_to, DATE_FORMAT_FR))
            paymenthistory['name'] = search_paymenthistory.name
            paymenthistory['number'] = search_paymenthistory.number
            paymenthistory['code'] = search_paymenthistory.code
            paymenthistory['contract'] = search_paymenthistory.contract_id.name
            if search_paymenthistory.code:
                paymenthistory['amount'] = search_paymenthistory.line_ids.filtered(lambda line: line.salary_rule_id.code == search_paymenthistory.code).mapped('amount')[0] if (len(list(search_paymenthistory.line_ids)) > 0 and len(list(search_paymenthistory.line_ids.filtered(lambda line: line.salary_rule_id.code == search_paymenthistory.code))) > 0) else 0.0
            else:
                paymenthistory['amount'] = search_paymenthistory.line_ids.mapped('amount')[0] if len(list(search_paymenthistory.line_ids)) > 0 else 0.0
            paymenthistory['number_of_hours'] = sum(search_paymenthistory.worked_days_line_ids.mapped('number_of_hours')) if len(list(search_paymenthistory.worked_days_line_ids)) > 0 else 0.0
            paymenthistory['state'] = STATUS_PAYMENT[search_paymenthistory.state]
            paymenthistories.append(paymenthistory)
            total_amount += paymenthistory['amount']
            total_number_of_hours += paymenthistory['number_of_hours']
        total_amount = round(total_amount, 2)
        total_number_of_hours = round(total_number_of_hours, 2)
        return http.request.render('siantou_ems_portal.siantou_ems_portal_paymenthistory_views',
                                {
                                    'paymenthistories': paymenthistories,
                                    'page_name': 'paymenthistory',
                                    'paymenthistory': 0,
                                    'total_amount': total_amount,
                                    'total_number_of_hours': total_number_of_hours,
                                })

    @http.route(['/my/accountbalance'], type='http', auth="user", website=True)
    def portal_accountbalance(self, search='', search_in='all', selected_month='0', **kw):
        selected_month_total = [str(i) for i in range(6)]
        if selected_month not in selected_month_total:
            selected_month = '0'
        if selected_month == selected_month_total[-1]:
            accountbalance_selected_month = 0
        else:
            accountbalance_selected_month = int(selected_month) + 1

        key_payslips = {}
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
        if is_user:
            if is_user == 'is_teacher':
                order = 'date_from asc'
                paymenthistories = http.request.env['hr.payslip'].sudo().search([('employee_id', '=', user.id)], order=order)
                paymenthistories = list(paymenthistories)
                for paymenthistory in paymenthistories:
                    for worked_days_line_id in paymenthistory.worked_days_line_ids:
                        end_time = Helpers.convert_float_to_time(worked_days_line_id.timetable_id.end_time, True)
                        start_time = Helpers.convert_float_to_time(worked_days_line_id.timetable_id.start_time, True)
                        key = '{}-{}-{}-{}'.format(worked_days_line_id.timetable_id.employee_id.id, worked_days_line_id.timetable_id.date, start_time, end_time)
                        if key not in key_payslips:
                            key_payslips[key] = {}
                            key_payslips[key]['timetable_id'] = worked_days_line_id.timetable_id.id
                            key_payslips[key]['rate'] = worked_days_line_id.rate
                            key_payslips[key]['amount'] = worked_days_line_id.amount

        timetable_ids = [payslip['timetable_id'] for payslip in key_payslips.values()]

        # Utilisation de la fonction du helper
        search_accountbalances, searchbar_inputs, search_month = Helpers.accountbalance(search, search_in, selected_month)
        total_rate = 0.0
        total_number_of_hours = 0.0
        accountbalances = []
        shared_subjects = {}
        for search_accountbalance in search_accountbalances:
            end_time = Helpers.convert_float_to_time(search_accountbalance.end_time, True)
            start_time = Helpers.convert_float_to_time(search_accountbalance.start_time, True)
            key = '{}-{}-{}-{}'.format(search_accountbalance.employee_id.id, search_accountbalance.date, start_time, end_time)
            if key in key_payslips and key_payslips[key]['timetable_id'] != search_accountbalance.id:
                continue

            timetable_day = datetime.strftime(search_accountbalance.date, DATE_FORMAT)

            if timetable_day not in shared_subjects.keys():
                shared_subjects[timetable_day] = []

            if search_accountbalance.subject_id.shared_subject:
                if search_accountbalance.subject_id.id not in shared_subjects[timetable_day]:
                    shared_subjects[timetable_day].append(search_accountbalance.subject_id.id)
                else:
                    continue

            accountbalance = {}
            accountbalance['id'] = search_accountbalance.id
            accountbalance['name'] = search_accountbalance.name
            accountbalance['date'] = search_accountbalance.date
            accountbalance['date_of_week'] = datetime.strftime(search_accountbalance.date, DATE_FORMAT_FR)
            accountbalance['semester_name'] = search_accountbalance.semester_id.name
            accountbalance['cycle_name'] = search_accountbalance.cycle_id.name
            accountbalance['level_name'] = search_accountbalance.level_id.name
            accountbalance['field_of_study_id'] = search_accountbalance.field_of_study_id.id
            accountbalance['field_of_study_name'] = search_accountbalance.field_of_study_id.name
            accountbalance['specialty_name'] = search_accountbalance.specialty_id.name
            accountbalance['option_name'] = search_accountbalance.option_id.name
            accountbalance['class_id'] = search_accountbalance.class_id.id
            accountbalance['class_name'] = search_accountbalance.class_id.name
            accountbalance['department_id'] = search_accountbalance.department_id.id
            accountbalance['department_name'] = search_accountbalance.department_id.name
            accountbalance['subject_id'] = search_accountbalance.subject_id.id
            accountbalance['subject_name'] = search_accountbalance.subject_id.name
            accountbalance['subject_code'] = search_accountbalance.subject_id.code
            accountbalance['subject_hours_credit'] = search_accountbalance.subject_id.hours_credit
            accountbalance['subject_shared_subject'] = '(TC)' if search_accountbalance.subject_id.shared_subject else ''
            accountbalance['classroom_name'] = search_accountbalance.classroom_id.name
            accountbalance['building_name'] = search_accountbalance.classroom_id.building_id.name
            accountbalance['batch_name'] = search_accountbalance.batch_id.name
            accountbalance['employee_name'] = search_accountbalance.employee_id.name
            accountbalance['day_of_week'] = CURRENT_WEEKDAY[search_accountbalance.day_of_week]
            accountbalance['start_time'] = search_accountbalance.start_time
            accountbalance['end_time'] = search_accountbalance.end_time
            accountbalance['worked_start_time'] = search_accountbalance.worked_start_time
            accountbalance['worked_end_time'] = search_accountbalance.worked_end_time
            accountbalance['not_active_slotitems'] = search_accountbalance.not_active_slotitems
            accountbalance['time_of_week'] = '{}-{}'.format(Helpers.convert_float_to_time(search_accountbalance.start_time), Helpers.convert_float_to_time(search_accountbalance.end_time))
            accountbalance['status'] = STATUS_TIMETABLE[search_accountbalance.status]

            if search_accountbalance.status == 'present':
                end_time = Helpers.convert_float_to_time(search_accountbalance.worked_end_time, True)
                start_time = Helpers.convert_float_to_time(search_accountbalance.worked_start_time, True)
                datetime_to = datetime.strptime(f"{search_accountbalance.date} {end_time}", DATETIME_FORMAT)
                datetime_from = datetime.strptime(f"{search_accountbalance.date} {start_time}", DATETIME_FORMAT)
                weekly_hours_credit = datetime_to - datetime_from
                weekly_hours_credit = weekly_hours_credit - timedelta(hours=search_accountbalance.not_active_slotitems)
                weekly_hours_credit = weekly_hours_credit.total_seconds() / 3600.0
                weekly_hours_credit = round(weekly_hours_credit, 2)
                accountbalance['number_of_hours'] = weekly_hours_credit
            else:
                end_time = Helpers.convert_float_to_time(search_accountbalance.end_time, True)
                start_time = Helpers.convert_float_to_time(search_accountbalance.start_time, True)
                datetime_to = datetime.strptime(f"{search_accountbalance.date} {end_time}", DATETIME_FORMAT)
                datetime_from = datetime.strptime(f"{search_accountbalance.date} {start_time}", DATETIME_FORMAT)
                weekly_hours_credit = datetime_to - datetime_from
                weekly_hours_credit = weekly_hours_credit - timedelta(hours=search_accountbalance.not_active_slotitems)
                weekly_hours_credit = weekly_hours_credit.total_seconds() / 3600.0
                weekly_hours_credit = round(weekly_hours_credit, 2)
                accountbalance['number_of_hours'] = weekly_hours_credit

            if len(search_accountbalance.employee_id.diplome_ids.ids) > 0:
                domain = [
                    ('school_id', '=', search_accountbalance.school_id.id),
                    ('cycle_id', '=', search_accountbalance.cycle_id.id),
                    ('level_id', '=', search_accountbalance.level_id.id),
                    ('type_cour', '=', search_accountbalance.type_cour),
                    ('diplome_availability_id.diplome_ids', 'in', search_accountbalance.employee_id.diplome_ids.ids),
                ]
            else:
                domain = [
                    ('school_id', '=', search_accountbalance.school_id.id),
                    ('cycle_id', '=', search_accountbalance.cycle_id.id),
                    ('level_id', '=', search_accountbalance.level_id.id),
                    ('type_cour', '=', search_accountbalance.type_cour),
                ]

            hourly_rates = http.request.env['siantou.ems.core.hourly.rate'].sudo().search(domain)
            hourly_rates = list(hourly_rates)

            min_hourly_rate = None
            min_teacher_hourly_rate = None
            if len(hourly_rates) > 0:
                for hourly_rate in hourly_rates:
                    domain = [
                        ('hourly_rate_id', '=', hourly_rate.id),
                        ('employee_id', '=', search_accountbalance.employee_id.id),
                        # ('subject_id', '=', search_accountbalance.subject_id.id),
                    ]

                    teacher_hourly_rates = http.request.env['siantou.ems.core.teacher.hourly.rate'].sudo().search(domain, limit=1)
                    teacher_hourly_rates = list(teacher_hourly_rates)
                    if len(teacher_hourly_rates) > 0:
                        for teacher_hourly_rate in teacher_hourly_rates:
                            if not min_teacher_hourly_rate:
                                min_teacher_hourly_rate = teacher_hourly_rate.rate
                            else:
                                if teacher_hourly_rate.rate < min_teacher_hourly_rate:
                                    min_teacher_hourly_rate = teacher_hourly_rate.rate
                    if not min_hourly_rate:
                        min_hourly_rate = hourly_rate.rate
                    else:
                        if hourly_rate.rate < min_hourly_rate:
                            min_hourly_rate = hourly_rate.rate

            if min_teacher_hourly_rate:
                accountbalance['rate'] = min_teacher_hourly_rate
            elif min_hourly_rate:
                accountbalance['rate'] = min_hourly_rate
            else:
                accountbalance['rate'] = 0.0

            accountbalance['amount'] = accountbalance['rate'] * accountbalance['number_of_hours']
            accountbalance['amount'] = round(accountbalance['amount'], 2)

            if search_accountbalance.employee_id.is_permanent:
                accountbalance['rate'] = 0.0
                accountbalance['amount'] = 0.0

            end_time = Helpers.convert_float_to_time(search_accountbalance.end_time, True)
            start_time = Helpers.convert_float_to_time(search_accountbalance.start_time, True)
            key = '{}-{}-{}-{}'.format(search_accountbalance.employee_id.id, search_accountbalance.date, start_time, end_time)
            if key in key_payslips:
                accountbalance['rate'] = key_payslips[key]['rate']
                accountbalance['amount'] = key_payslips[key]['amount']

            accountbalances.append(accountbalance)
            total_rate += accountbalance['amount']
            total_number_of_hours += accountbalance['number_of_hours']
        total_rate = round(total_rate, 2)
        total_number_of_hours = round(total_number_of_hours, 2)
        accountbalances = Helpers.format_accountbalance(accountbalances)
        return http.request.render('siantou_ems_portal.siantou_ems_portal_accountbalance_views',
                                {
                                    'accountbalances': accountbalances,
                                    'page_name': 'accountbalance',
                                    'accountbalance': 0,
                                    'total_rate': total_rate,
                                    'total_number_of_hours': total_number_of_hours,
                                    'accountbalance_selected_month': accountbalance_selected_month,
                                    'search_month': search_month,
                                })

    @http.route(['/my/consumptionhour'], type='http', auth="user", website=True)
    def portal_consumptionhour(self, search='', search_in='all', **kw):
        # Utilisation de la fonction du helper
        search_consumptionhours, searchbar_inputs = Helpers.consumptionhour(search, search_in)
        consumptionhours = []
        for search_consumptionhour in search_consumptionhours:
            consumptionhour = {}
            consumptionhour['id'] = search_consumptionhour.id
            consumptionhour['name'] = search_consumptionhour.name
            consumptionhour['date'] = search_consumptionhour.date
            consumptionhour['date_of_week'] = datetime.strftime(search_consumptionhour.date, DATE_FORMAT_FR)
            consumptionhour['semester_name'] = search_consumptionhour.semester_id.name
            consumptionhour['cycle_name'] = search_consumptionhour.cycle_id.name
            consumptionhour['level_name'] = search_consumptionhour.level_id.name
            consumptionhour['field_of_study_id'] = search_consumptionhour.field_of_study_id.id
            consumptionhour['field_of_study_name'] = search_consumptionhour.field_of_study_id.name
            consumptionhour['specialty_name'] = search_consumptionhour.specialty_id.name
            consumptionhour['option_name'] = search_consumptionhour.option_id.name
            consumptionhour['class_id'] = search_consumptionhour.class_id.id
            consumptionhour['class_name'] = search_consumptionhour.class_id.name
            consumptionhour['department_id'] = search_consumptionhour.department_id.id
            consumptionhour['department_name'] = search_consumptionhour.department_id.name
            consumptionhour['subject_id'] = search_consumptionhour.subject_id.id
            consumptionhour['subject_name'] = search_consumptionhour.subject_id.name
            consumptionhour['subject_code'] = search_consumptionhour.subject_id.code
            consumptionhour['subject_hours_credit'] = search_consumptionhour.subject_id.hours_credit
            consumptionhour['subject_shared_subject'] = search_consumptionhour.subject_id.shared_subject
            consumptionhour['classroom_name'] = search_consumptionhour.classroom_id.name
            consumptionhour['building_name'] = search_consumptionhour.classroom_id.building_id.name
            consumptionhour['batch_name'] = search_consumptionhour.batch_id.name
            consumptionhour['employee_name'] = search_consumptionhour.employee_id.name
            consumptionhour['day_of_week'] = CURRENT_WEEKDAY[search_consumptionhour.day_of_week]
            consumptionhour['start_time'] = search_consumptionhour.start_time
            consumptionhour['end_time'] = search_consumptionhour.end_time
            consumptionhour['worked_start_time'] = search_consumptionhour.worked_start_time
            consumptionhour['worked_end_time'] = search_consumptionhour.worked_end_time
            consumptionhour['not_active_slotitems'] = search_consumptionhour.not_active_slotitems
            consumptionhour['status'] = search_consumptionhour.status
            consumptionhours.append(consumptionhour)
        consumptionhours = Helpers.format_consumptionhour(consumptionhours)
        return http.request.render('siantou_ems_portal.siantou_ems_portal_consumptionhour_views',
                                {
                                    'consumptionhours': consumptionhours,
                                    'page_name': 'consumptionhour',
                                    'consumptionhour': 0,
                                })

    @http.route(['/my/progressreport'], type='http', auth="user", website=True)
    def portal_progressreport(self, search='', search_in='all', **kw):
        # Utilisation de la fonction du helper
        search_progressreports, searchbar_inputs = Helpers.progressreport(search, search_in)
        progressreports = []
        for search_progressreport in search_progressreports:
            progressreport = {}
            progressreport['id'] = search_progressreport.id
            progressreport['name'] = search_progressreport.name
            progressreport['date'] = search_progressreport.date
            progressreport['date_of_week'] = datetime.strftime(search_progressreport.date, DATE_FORMAT_FR)
            progressreport['semester_name'] = search_progressreport.semester_id.name
            progressreport['cycle_name'] = search_progressreport.cycle_id.name
            progressreport['level_name'] = search_progressreport.level_id.name
            progressreport['field_of_study_id'] = search_progressreport.field_of_study_id.id
            progressreport['field_of_study_name'] = search_progressreport.field_of_study_id.name
            progressreport['specialty_name'] = search_progressreport.specialty_id.name
            progressreport['option_name'] = search_progressreport.option_id.name
            progressreport['class_id'] = search_progressreport.class_id.id
            progressreport['class_name'] = search_progressreport.class_id.name
            progressreport['department_id'] = search_progressreport.department_id.id
            progressreport['department_name'] = search_progressreport.department_id.name
            progressreport['subject_id'] = search_progressreport.subject_id.id
            progressreport['subject_name'] = search_progressreport.subject_id.name
            progressreport['subject_code'] = search_progressreport.subject_id.code
            progressreport['subject_hours_credit'] = search_progressreport.subject_id.hours_credit
            progressreport['subject_shared_subject'] = search_progressreport.subject_id.shared_subject
            progressreport['classroom_name'] = search_progressreport.classroom_id.name
            progressreport['building_name'] = search_progressreport.classroom_id.building_id.name
            progressreport['batch_name'] = search_progressreport.batch_id.name
            progressreport['employee_name'] = search_progressreport.employee_id.name
            progressreport['day_of_week'] = CURRENT_WEEKDAY[search_progressreport.day_of_week]
            progressreport['start_time'] = search_progressreport.start_time
            progressreport['end_time'] = search_progressreport.end_time
            progressreport['worked_start_time'] = search_progressreport.worked_start_time
            progressreport['worked_end_time'] = search_progressreport.worked_end_time
            progressreport['not_active_slotitems'] = search_progressreport.not_active_slotitems
            progressreport['status'] = search_progressreport.status
            session_ids = search_progressreport.session_ids
            session_ids = list(session_ids)
            sessions = []
            for session_id in session_ids:
                session = {}
                session['id'] = session_id.id
                session['name'] = session_id.name
                session['description'] = session_id.description
                session['timetable_id'] = session_id.timetable_id.id
                session['report_id'] = session_id.report_id.id
                sessions.append(session)
            progressreport['sessions'] = sessions
            progressreports.append(progressreport)
        progressreports = Helpers.format_progressreport(progressreports)
        return http.request.render('siantou_ems_portal.siantou_ems_portal_progressreport_views',
                                {
                                    'progressreports': progressreports,
                                    'page_name': 'progressreport',
                                    'progressreport': 0,
                                })

    @http.route(['/my/subjectsession/<int:classe>/<int:subject>/list'], type='http', auth="user", website=True)
    def portal_subjectsession_list(self, classe=None, subject=None, search='', search_in='all', **kw):
        # Utilisation de la fonction du helper
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
        class_id = http.request.env['siantou.ems.core.class'].sudo().search([('id', '=', classe)], limit=1)
        subject_id = http.request.env['siantou.ems.core.subject'].sudo().search([('id', '=', subject)], limit=1)
        params = {}
        params['class_id'] = class_id.id
        params['class_name'] = class_id.name
        params['subject_id'] = subject_id.id
        params['subject_name'] = subject_id.name
        search_subjectsessions, searchbar_inputs = Helpers.subjectsession(search, search_in, class_id=class_id, subject_id=subject_id)
        subjectsessions = []
        for search_subjectsession in search_subjectsessions:
            subjectsession = {}
            subjectsession['id'] = search_subjectsession.id
            subjectsession['name'] = search_subjectsession.name
            subjectsession['date'] = search_subjectsession.date
            subjectsession['date_of_week'] = datetime.strftime(search_subjectsession.date, DATE_FORMAT_FR)
            subjectsession['semester_name'] = search_subjectsession.semester_id.name
            subjectsession['cycle_name'] = search_subjectsession.cycle_id.name
            subjectsession['level_name'] = search_subjectsession.level_id.name
            subjectsession['field_of_study_id'] = search_subjectsession.field_of_study_id.id
            subjectsession['field_of_study_name'] = search_subjectsession.field_of_study_id.name
            subjectsession['specialty_name'] = search_subjectsession.specialty_id.name
            subjectsession['option_name'] = search_subjectsession.option_id.name
            subjectsession['class_id'] = search_subjectsession.class_id.id
            subjectsession['class_name'] = search_subjectsession.class_id.name
            subjectsession['department_id'] = search_subjectsession.department_id.id
            subjectsession['department_name'] = search_subjectsession.department_id.name
            subjectsession['subject_id'] = search_subjectsession.subject_id.id
            subjectsession['subject_name'] = search_subjectsession.subject_id.name
            subjectsession['subject_code'] = search_subjectsession.subject_id.code
            subjectsession['subject_hours_credit'] = search_subjectsession.subject_id.hours_credit
            subjectsession['subject_shared_subject'] = search_subjectsession.subject_id.shared_subject
            subjectsession['classroom_name'] = search_subjectsession.classroom_id.name
            subjectsession['building_name'] = search_subjectsession.classroom_id.building_id.name
            subjectsession['batch_name'] = search_subjectsession.batch_id.name
            subjectsession['employee_name'] = search_subjectsession.employee_id.name
            subjectsession['day_of_week'] = CURRENT_WEEKDAY[search_subjectsession.day_of_week]
            subjectsession['start_time'] = search_subjectsession.start_time
            subjectsession['end_time'] = search_subjectsession.end_time
            subjectsession['worked_start_time'] = search_subjectsession.worked_start_time
            subjectsession['worked_end_time'] = search_subjectsession.worked_end_time
            subjectsession['not_active_slotitems'] = search_subjectsession.not_active_slotitems
            subjectsession['status'] = search_subjectsession.status
            session_ids = search_subjectsession.session_ids
            session_ids = list(session_ids)
            sessions = []
            for session_id in session_ids:
                session = {}
                session['id'] = session_id.id
                session['name'] = session_id.name
                session['description'] = session_id.description
                session['timetable_id'] = session_id.timetable_id.id
                session['report_id'] = session_id.report_id.id
                sessions.append(session)
            subjectsession['sessions'] = sessions
            subjectsessions.append(subjectsession)
        subjectsessions = Helpers.format_subjectsession(subjectsessions)
        return http.request.render('siantou_ems_portal.siantou_ems_portal_subjectsession_list_views',
                                {
                                    'subjectsessions': subjectsessions,
                                    'page_name': 'subjectsession_list',
                                    'subjectsession_list': 0,
                                    'is_user': 'is_teacher' if is_user and is_user == 'is_teacher' else '',
                                    'params': params,
                                })

    @http.route(['/my/subjectsession/<int:classe>/<int:subject>/new'], type='http', auth="user", website=True)
    def portal_subjectsession_new(self, classe=None, subject=None, search='', search_in='all', **kw):
        # Utilisation de la fonction du helper
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
        class_id = http.request.env['siantou.ems.core.class'].sudo().search([('id', '=', classe)], limit=1)
        subject_id = http.request.env['siantou.ems.core.subject'].sudo().search([('id', '=', subject)], limit=1)
        params = {}
        params['class_id'] = class_id.id
        params['class_name'] = class_id.name
        params['subject_id'] = subject_id.id
        params['subject_name'] = subject_id.name
        search_subjectsessions, searchbar_inputs = Helpers.subjectsession(search, search_in, class_id=class_id, subject_id=subject_id)
        subjectsessions = []
        for search_subjectsession in search_subjectsessions:
            subjectsession = {}
            subjectsession['id'] = search_subjectsession.id
            subjectsession['name'] = search_subjectsession.name
            subjectsession['date'] = search_subjectsession.date
            subjectsession['date_of_week'] = datetime.strftime(search_subjectsession.date, DATE_FORMAT_FR)
            subjectsession['semester_name'] = search_subjectsession.semester_id.name
            subjectsession['cycle_name'] = search_subjectsession.cycle_id.name
            subjectsession['level_name'] = search_subjectsession.level_id.name
            subjectsession['field_of_study_id'] = search_subjectsession.field_of_study_id.id
            subjectsession['field_of_study_name'] = search_subjectsession.field_of_study_id.name
            subjectsession['specialty_name'] = search_subjectsession.specialty_id.name
            subjectsession['option_name'] = search_subjectsession.option_id.name
            subjectsession['class_id'] = search_subjectsession.class_id.id
            subjectsession['class_name'] = search_subjectsession.class_id.name
            subjectsession['department_id'] = search_subjectsession.department_id.id
            subjectsession['department_name'] = search_subjectsession.department_id.name
            subjectsession['subject_id'] = search_subjectsession.subject_id.id
            subjectsession['subject_name'] = search_subjectsession.subject_id.name
            subjectsession['subject_code'] = search_subjectsession.subject_id.code
            subjectsession['subject_hours_credit'] = search_subjectsession.subject_id.hours_credit
            subjectsession['subject_shared_subject'] = search_subjectsession.subject_id.shared_subject
            subjectsession['classroom_name'] = search_subjectsession.classroom_id.name
            subjectsession['building_name'] = search_subjectsession.classroom_id.building_id.name
            subjectsession['batch_name'] = search_subjectsession.batch_id.name
            subjectsession['employee_name'] = search_subjectsession.employee_id.name
            subjectsession['day_of_week'] = CURRENT_WEEKDAY[search_subjectsession.day_of_week]
            subjectsession['start_time'] = search_subjectsession.start_time
            subjectsession['end_time'] = search_subjectsession.end_time
            subjectsession['worked_start_time'] = search_subjectsession.worked_start_time
            subjectsession['worked_end_time'] = search_subjectsession.worked_end_time
            subjectsession['not_active_slotitems'] = search_subjectsession.not_active_slotitems
            subjectsession['status'] = search_subjectsession.status
            session_ids = search_subjectsession.session_ids
            session_ids = list(session_ids)
            sessions = []
            for session_id in session_ids:
                session = {}
                session['id'] = session_id.id
                session['name'] = session_id.name
                session['description'] = session_id.description
                session['timetable_id'] = session_id.timetable_id.id
                session['report_id'] = session_id.report_id.id
                sessions.append(session)
            subjectsession['sessions'] = sessions
            subjectsessions.append(subjectsession)
        subjectsessions = Helpers.format_subjectsession(subjectsessions)
        all_timetables = []
        timetables = subjectsessions.keys()
        for timetable in timetables:
            if len(subjectsessions[timetable]['data']) == 0:
                all_timetables.append(subjectsessions[timetable])
        name = None
        description = None
        timetable_id = None
        return http.request.render('siantou_ems_portal.siantou_ems_portal_subjectsession_new_views',
                                {
                                    'subjectsessions': subjectsessions,
                                    'page_name': 'subjectsession_new',
                                    'subjectsession_new': 0,
                                    'is_user': 'is_teacher' if is_user and is_user == 'is_teacher' else '',
                                    'params': params,
                                    'name': '',
                                    'description': '',
                                    'all_timetables': all_timetables,
                                    'timetable': timetable_id,
                                })

    @http.route(['/my/subjectsession/create'], type='http', auth="user", website=True, methods=['POST'])
    def portal_subjectsession_create(self, **kw):
        classe = int(kw.get('classe')),
        subject = int(kw.get('subject')),
        class_id = http.request.env['siantou.ems.core.class'].sudo().search([('id', '=', classe)], limit=1)
        subject_id = http.request.env['siantou.ems.core.subject'].sudo().search([('id', '=', subject)], limit=1)
        params = {}
        params['class_id'] = class_id.id
        params['subject_id'] = subject_id.id
        if not kw.get('timetable'):
            return http.request.redirect('/my/subjectsession/{}/{}/new'.format(params['class_id'], params['subject_id']))
        vals = {
            'description': kw.get('description'),
            'timetable_id': int(kw.get('timetable')),
        }
        timetable = http.request.env['siantou.ems.timetable.timetable'].sudo().search([
            '|',
            '&',
            ('group_id.is_active', '=', True),
            ('group_id.is_submit', '=', False),
            '&',
            ('group_parent_id.is_active', '=', True),
            ('group_parent_id.is_submit', '=', False),
            ('id', '=', vals['timetable_id'])
        ], limit=1)
        timetable_ids = http.request.env['siantou.ems.timetable.timetable'].sudo().search([
            '|',
            '&',
            ('group_id.is_active', '=', True),
            ('group_id.is_submit', '=', False),
            '&',
            ('group_parent_id.is_active', '=', True),
            ('group_parent_id.is_submit', '=', False),
            ('employee_id', '=', timetable.employee_id.id),
            # ('subject_id', '=', timetable.subject_id.id),
            ('date', '=', timetable.date),
            ('start_time', '=', timetable.start_time),
            ('end_time', '=', timetable.end_time),
        ])
        for timetable_id in timetable_ids:
            vals['timetable_id'] = timetable_id.id
            report_id = http.request.env['siantou.ems.core.progress.report'].sudo().search([
                ('class_id', '=', timetable_id.class_id.id),
                ('subject_id', '=', timetable_id.subject_id.id),
            ], limit=1)
            if not report_id:
                report_id = http.request.env['siantou.ems.core.progress.report'].sudo().create({
                    'class_id': timetable_id.class_id.id,
                    'subject_id': timetable_id.subject_id.id,
                })
            session_id = http.request.env['siantou.ems.core.subject.session'].sudo().search([
                ('timetable_id', '=', timetable_id.id),
                ('report_id', '=', report_id.id),
            ], limit=1)
            if not session_id:
                vals['report_id'] = report_id.id
                session_id = http.request.env['siantou.ems.core.subject.session'].sudo().create(vals)
            else:
                del(vals['timetable_id'])
                session_id.sudo().write(vals)
        return http.request.redirect('/my/subjectsession/{}/{}/list'.format(params['class_id'], params['subject_id']))

    @http.route(['/my/subjectsession/<int:classe>/<int:subject>/<int:session>/edit'], type='http', auth="user", website=True)
    def portal_subjectsession_edit(self, classe=None, subject=None, session=None, search='', search_in='all', **kw):
        # Utilisation de la fonction du helper
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
        class_id = http.request.env['siantou.ems.core.class'].sudo().search([('id', '=', classe)], limit=1)
        subject_id = http.request.env['siantou.ems.core.subject'].sudo().search([('id', '=', subject)], limit=1)
        session_id = http.request.env['siantou.ems.core.subject.session'].sudo().search([('id', '=', session)], limit=1)
        params = {}
        params['class_id'] = class_id.id
        params['class_name'] = class_id.name
        params['subject_id'] = subject_id.id
        params['subject_name'] = subject_id.name
        params['session_id'] = session_id.id
        search_subjectsessions, searchbar_inputs = Helpers.subjectsession(search, search_in, class_id=class_id, subject_id=subject_id)
        subjectsessions = []
        for search_subjectsession in search_subjectsessions:
            subjectsession = {}
            subjectsession['id'] = search_subjectsession.id
            subjectsession['name'] = search_subjectsession.name
            subjectsession['date'] = search_subjectsession.date
            subjectsession['date_of_week'] = datetime.strftime(search_subjectsession.date, DATE_FORMAT_FR)
            subjectsession['semester_name'] = search_subjectsession.semester_id.name
            subjectsession['cycle_name'] = search_subjectsession.cycle_id.name
            subjectsession['level_name'] = search_subjectsession.level_id.name
            subjectsession['field_of_study_id'] = search_subjectsession.field_of_study_id.id
            subjectsession['field_of_study_name'] = search_subjectsession.field_of_study_id.name
            subjectsession['specialty_name'] = search_subjectsession.specialty_id.name
            subjectsession['option_name'] = search_subjectsession.option_id.name
            subjectsession['class_id'] = search_subjectsession.class_id.id
            subjectsession['class_name'] = search_subjectsession.class_id.name
            subjectsession['department_id'] = search_subjectsession.department_id.id
            subjectsession['department_name'] = search_subjectsession.department_id.name
            subjectsession['subject_id'] = search_subjectsession.subject_id.id
            subjectsession['subject_name'] = search_subjectsession.subject_id.name
            subjectsession['subject_code'] = search_subjectsession.subject_id.code
            subjectsession['subject_hours_credit'] = search_subjectsession.subject_id.hours_credit
            subjectsession['subject_shared_subject'] = search_subjectsession.subject_id.shared_subject
            subjectsession['classroom_name'] = search_subjectsession.classroom_id.name
            subjectsession['building_name'] = search_subjectsession.classroom_id.building_id.name
            subjectsession['batch_name'] = search_subjectsession.batch_id.name
            subjectsession['employee_name'] = search_subjectsession.employee_id.name
            subjectsession['day_of_week'] = CURRENT_WEEKDAY[search_subjectsession.day_of_week]
            subjectsession['start_time'] = search_subjectsession.start_time
            subjectsession['end_time'] = search_subjectsession.end_time
            subjectsession['worked_start_time'] = search_subjectsession.worked_start_time
            subjectsession['worked_end_time'] = search_subjectsession.worked_end_time
            subjectsession['not_active_slotitems'] = search_subjectsession.not_active_slotitems
            subjectsession['status'] = search_subjectsession.status
            session_ids = search_subjectsession.session_ids
            session_ids = list(session_ids)
            sessions = []
            for session_id in session_ids:
                session = {}
                session['id'] = session_id.id
                session['name'] = session_id.name
                session['description'] = session_id.description
                session['timetable_id'] = session_id.timetable_id.id
                session['report_id'] = session_id.report_id.id
                sessions.append(session)
            subjectsession['sessions'] = sessions
            subjectsessions.append(subjectsession)
        subjectsessions = Helpers.format_subjectsession(subjectsessions)
        session_id = http.request.env['siantou.ems.core.subject.session'].sudo().search([('id', '=', params['session_id'])], limit=1)
        timetable = subjectsessions[str(session_id.timetable_id.id)]
        params['session_name'] = timetable['date'] + ' ' + timetable['start_time'] + '-' + timetable['end_time']
        name = session_id.name
        description = session_id.description
        return http.request.render('siantou_ems_portal.siantou_ems_portal_subjectsession_edit_views',
                                {
                                    'subjectsessions': subjectsessions,
                                    'page_name': 'subjectsession_edit',
                                    'subjectsession_edit': 0,
                                    'is_user': 'is_teacher' if is_user and is_user == 'is_teacher' else '',
                                    'params': params,
                                    'name': name,
                                    'description': description,
                                })

    @http.route(['/my/subjectsession/update'], type='http', auth="user", website=True, methods=['POST'])
    def portal_subjectsession_update(self, **kw):
        classe = int(kw.get('classe')),
        subject = int(kw.get('subject')),
        session = int(kw.get('session')),
        class_id = http.request.env['siantou.ems.core.class'].sudo().search([('id', '=', classe)], limit=1)
        subject_id = http.request.env['siantou.ems.core.subject'].sudo().search([('id', '=', subject)], limit=1)
        session_id = http.request.env['siantou.ems.core.subject.session'].sudo().search([('id', '=', session)], limit=1)
        params = {}
        params['class_id'] = class_id.id
        params['subject_id'] = subject_id.id
        params['session_id'] = session_id.id
        vals = {
            'description': kw.get('description'),
        }
        timetable = session_id.timetable_id
        timetable_ids = http.request.env['siantou.ems.timetable.timetable'].sudo().search([
            '|',
            '&',
            ('group_id.is_active', '=', True),
            ('group_id.is_submit', '=', False),
            '&',
            ('group_parent_id.is_active', '=', True),
            ('group_parent_id.is_submit', '=', False),
            ('employee_id', '=', timetable.employee_id.id),
            # ('subject_id', '=', timetable.subject_id.id),
            ('date', '=', timetable.date),
            ('start_time', '=', timetable.start_time),
            ('end_time', '=', timetable.end_time),
        ])
        for timetable_id in timetable_ids:
            session_id = http.request.env['siantou.ems.core.subject.session'].sudo().search([('timetable_id', '=', timetable_id.id)], limit=1)
            if not session_id:
                vals['timetable_id'] = timetable_id.id
                report_id = http.request.env['siantou.ems.core.progress.report'].sudo().search([
                    ('class_id', '=', timetable_id.class_id.id),
                    ('subject_id', '=', timetable_id.subject_id.id),
                ], limit=1)
                if not report_id:
                    report_id = http.request.env['siantou.ems.core.progress.report'].sudo().create({
                        'class_id': timetable_id.class_id.id,
                        'subject_id': timetable_id.subject_id.id,
                    })
                session_id = http.request.env['siantou.ems.core.subject.session'].sudo().search([
                    ('timetable_id', '=', timetable_id.id),
                    ('report_id', '=', report_id.id),
                ], limit=1)
                if not session_id:
                    vals['report_id'] = report_id.id
                    session_id = http.request.env['siantou.ems.core.subject.session'].sudo().create(vals)
                else:
                    del(vals['timetable_id'])
                    session_id.sudo().write(vals)
            else:
                session_id.sudo().write(vals)
        return http.request.redirect('/my/subjectsession/{}/{}/list'.format(params['class_id'], params['subject_id']))

    @http.route(['/my/calendar', '/my/calendar/page/<int:page>'], type='http', auth="user", website=True)
    def portal_calendar(self, page=1, search='', search_in='all', **kw):
        # Utilisation de la fonction du helper
        search_calendars, searchbar_inputs, search_year = Helpers.calendar(search, search_in)
        calendars = []
        for search_calendar in search_calendars:
            calendar = {}
            calendar['id'] = search_calendar.id
            calendar['name'] = search_calendar.name
            calendar['start'] = search_calendar.start
            calendar['start_date'] = datetime.strftime(search_calendar.start, DATETIME_FORMAT_FR)
            calendar['stop'] = search_calendar.stop
            calendar['stop_date'] = datetime.strftime(search_calendar.stop, DATETIME_FORMAT_FR)
            calendar['location'] = search_calendar.location
            calendar['duration'] = search_calendar.duration
            calendars.append(calendar)
        calendars, search_year = Helpers.format_calendar(calendars, search_year)
        if search_year in calendars:
            calendars = calendars[search_year]
        current_calendars = {}
        for month in calendars.keys():
            if calendars[month]['is_current_month']:
                current_calendars[month] = calendars[month]
        calendars = Helpers.paginate_calendar(calendars, 1, page)
        return http.request.render(f'siantou_ems_portal.siantou_ems_portal_calendar_calendar_views',
                                {
                                    'calendars': calendars['pages'],
                                    'calendar_pages_total': calendars['pages_total'],
                                    'calendar_page_number': page,
                                    'current_calendars': current_calendars,
                                    'search_year': search_year,
                                    'page_name': 'calendar',
                                    'calendar': 0,
                                    'search': search,
                                    'search_in': search_in,
                                    'searchbar_inputs': searchbar_inputs,
                                })

    @http.route(['/my/notification'], type='http', auth="user", website=True)
    def portal_notification(self, search='', search_in='all', **kw):
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
            elif search_notification.template == 'om_hr_payroll.om_hr_payroll_template_timetable_notification_rappel':
                notification['subject_name'] = search_notification.timetable_id.subject_id.name
                notification['subject_code'] = search_notification.timetable_id.subject_id.code
                notification['classroom_name'] = search_notification.timetable_id.classroom_id.name
                notification['building_name'] = search_notification.timetable_id.classroom_id.building_id.name
            elif search_notification.template == 'om_hr_payroll.om_hr_payroll_template_timetable_notification_retard':
                notification['subject_name'] = search_notification.timetable_id.subject_id.name
                notification['subject_code'] = search_notification.timetable_id.subject_id.code
                notification['classroom_name'] = search_notification.timetable_id.classroom_id.name
                notification['building_name'] = search_notification.timetable_id.classroom_id.building_id.name
            elif search_notification.template == 'om_hr_payroll.om_hr_payroll_template_timetable_notification_exception':
                notification['subject_name'] = ''
                notification['subject_code'] = ''
                notification['classroom_name'] = ''
                notification['building_name'] = ''
            else:
                notification['subject_name'] = ''
                notification['subject_code'] = ''
                notification['classroom_name'] = ''
                notification['building_name'] = ''
            notification['template'] = search_notification.template
            notification['message'] = search_notification.message
            notification['status'] = STATUS_NOTIFICATION[search_notification.status]
            notifications.append(notification)
        return http.request.render('siantou_ems_portal.siantou_ems_portal_notification_views',
                                {
                                    'notifications': notifications,
                                    'page_name': 'notification',
                                    'notification': 0,
                                })

    @http.route(['/my/requireddata'], type='http', auth="user", website=True)
    def portal_requireddata(self, **kw):
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
            return http.request.redirect('/my/home')
        elif http.request.env.user.student_id.id:
            user = http.request.env.user.student_id
            is_user = 'is_student'
        if is_user:
            private_phone = user.private_phone
            private_email = user.private_email
            date_naissance = user.date_naissance
            nationalite = user.nationalite.id
            city_id = user.city_id.id
            quarter_id = user.quarter_id.id
        return http.request.render('siantou_ems_portal.siantou_ems_portal_requireddata_views',
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
                                    'page_name': 'requireddata',
                                    'requireddata': 0,
                                })

    @http.route(['/my/requireddata/create'], type='http', auth="user", website=True, methods=['POST'])
    def portal_requireddata_create(self, **kw):
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
        if is_user:
            if is_user == 'is_student':
                if not kw.get('phone'):
                    return http.request.redirect('/my/requireddata')
                if not kw.get('email'):
                    return http.request.redirect('/my/requireddata')
                if not kw.get('birthday'):
                    return http.request.redirect('/my/requireddata')
                if not kw.get('country'):
                    return http.request.redirect('/my/requireddata')
                if not kw.get('city'):
                    return http.request.redirect('/my/requireddata')
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
        return http.request.redirect('/my/home')

    @http.route(['/my/portal/switch'], type='http', auth="user", website=True)
    def portal_switch(self, search='', search_in='all', **kw):
        is_user = None
        if http.request.env.user.employee_id.id:
            user = http.request.env.user
            if http.request.env.user.employee_id.is_teacher and http.request.env.user.employee_id.is_portal:
                is_user = 'is_portal'
        if is_user:
            group_portal = http.request.env.ref('base.group_portal')
            group_public = http.request.env.ref('base.group_public')
            group_user = http.request.env.ref('base.group_user')
            group_portal.sudo().write({'users': [(3, user.id)]})
            group_user.sudo().write({'users': [(4, user.id)]})

            url_base = http.request.env['ir.config_parameter'].sudo().get_param(f'siantou.url_base', 'http://127.0.0.1:8069')
            url_portal = http.request.env['ir.config_parameter'].sudo().get_param(f'siantou.url_portal', '/my/home')
            url_user = http.request.env['ir.config_parameter'].sudo().get_param(f'siantou.url_user', '/web')

            return http.request.redirect(url_user)
        return http.request.redirect('/my/home')
