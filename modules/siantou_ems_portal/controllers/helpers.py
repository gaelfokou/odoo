# helpers.py
from odoo import http
from odoo.addons.portal.controllers import portal
from odoo.exceptions import UserError, ValidationError
import pandas as pd
import numpy as np
import re
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import pytz
import logging
import copy

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

_logger = logging.getLogger(__name__)

class Helpers:
    @staticmethod
    def timetable(search='', search_in='all', cycle_id=None, level_id=None, field_of_study_id=None, specialty_id=None, option_id=None, class_id=None):
        searchbar_inputs = {
            'all': {'label': 'Tout', 'input': 'all', 'domain': []},
            'cycle': {'label': 'Cycle', 'input': 'cycle', 'domain': [('cycle_id.name', 'like', search)]},
            'niveau': {'label': 'Niveau', 'input': 'niveau', 'domain': [('level_id.name', 'like', search)]},
            'filiere': {'label': 'Filière', 'input': 'filiere', 'domain': [('field_of_study_id.name', 'like', search)]},
            'specialite': {'label': 'Spécialité', 'input': 'specialite', 'domain': [('specialty_id.name', 'like', search)]},
            'option': {'label': 'Option', 'input': 'option', 'domain': [('option_id.name', 'like', search)]},
            'classe': {'label': 'Classe', 'input': 'classe', 'domain': [('class_id.name', 'like', search)]},
            'cours': {'label': 'Cours', 'input': 'cours', 'domain': [('subject_id.name', 'like', search)]},
            'enseignant': {'label': 'Enseignant', 'input': 'enseignant', 'domain': [('employee_id.name', 'like', search)]},
        }
        if search_in not in searchbar_inputs.keys():
            search_in = 'all'
        search_domain = searchbar_inputs[search_in]['domain']

        if cycle_id:
            search_domain.append(('cycle_id', '=', cycle_id.id))
        if level_id:
            search_domain.append(('level_id', '=', level_id.id))
        if field_of_study_id:
            search_domain.append(('field_of_study_id', '=', field_of_study_id.id))
        if specialty_id:
            search_domain.append(('specialty_id', '=', specialty_id.id))
        if option_id:
            search_domain.append(('option_id', '=', option_id.id))
        if class_id:
            search_domain.append(('class_id', '=', class_id.id))

        order = 'date asc'

        search_timetables = []
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
            if is_user == 'is_teacher':
                user = http.request.env.user.employee_id
                search_domain.append(('employee_id', '=', user.id))

                timetables = http.request.env['siantou.ems.timetable.timetable'].sudo().search(search_domain, order=order)
                timetables = list(timetables)
                search_timetables = timetables
            elif is_user == 'is_student':
                search_domain.append(('class_id', '=', user.class_id.id))

                timetables = http.request.env['siantou.ems.timetable.timetable'].sudo().search(search_domain, order=order)
                timetables = list(timetables)
                search_timetables = timetables

        _logger.info(f'----------- tototototototo search_timetables {search_timetables} -----------')

        return search_timetables, searchbar_inputs

    @staticmethod
    def schoolfee(search='', search_in='all'):
        searchbar_inputs = {
            'all': {'label': 'Tout', 'input': 'all', 'domain': []},
        }
        if search_in not in searchbar_inputs.keys():
            search_in = 'all'
        search_domain = searchbar_inputs[search_in]['domain']

        order = 'date_payment asc'

        search_schoolfees = []
        if http.request.env.user.student_id.id:
            user = http.request.env.user.student_id
            search_domain.append(('student_id', '=', user.id))

            schoolfees = http.request.env['education.fee.payment'].sudo().search(search_domain, order=order)
            schoolfees = list(schoolfees)
            search_schoolfees = schoolfees

            search_domain = []
            search_domain.append(('student_id', '=', user.id))

            schoolfees = http.request.env['education.fee.payment.enrollment'].sudo().search(search_domain, order=order)
            schoolfees = list(schoolfees)
            search_schoolfees += schoolfees

        _logger.info(f'----------- tototototototo search_schoolfees {search_schoolfees} -----------')

        return search_schoolfees, searchbar_inputs

    @staticmethod
    def paymenthistory(search='', search_in='all'):
        searchbar_inputs = {
            'all': {'label': 'Tout', 'input': 'all', 'domain': []},
        }
        if search_in not in searchbar_inputs.keys():
            search_in = 'all'
        search_domain = searchbar_inputs[search_in]['domain']

        order = 'date_from asc'

        search_paymenthistories = []
        if http.request.env.user.employee_id.id:
            if http.request.env.user.employee_id.is_teacher:
                user = http.request.env.user.employee_id
                search_domain.append(('employee_id', '=', user.id))

                paymenthistories = http.request.env['hr.payslip'].sudo().search(search_domain, order=order)
                paymenthistories = list(paymenthistories)
                search_paymenthistories = paymenthistories

        _logger.info(f'----------- tototototototo search_paymenthistories {search_paymenthistories} -----------')

        return search_paymenthistories, searchbar_inputs

    @staticmethod
    def accountbalance(end_date=None, start_date=None, search='', search_in='all'):
        searchbar_inputs = {
            'all': {'label': 'Tout', 'input': 'all', 'domain': []},
        }
        if search_in not in searchbar_inputs.keys():
            search_in = 'all'
        search_domain = searchbar_inputs[search_in]['domain']
        search_domain.append(('status', 'in', ['present', 'permission']))

        order = 'date asc'

        search_accountbalances = []
        if http.request.env.user.employee_id.id:
            if http.request.env.user.employee_id.is_teacher:
                user = http.request.env.user.employee_id
                search_domain.append(('employee_id', '=', user.id))

                search_timetables = http.request.env['siantou.ems.timetable.timetable'].sudo().search(search_domain, order=order)
                if start_date and end_date:
                    search_timetables = search_timetables.filtered(lambda rec: rec.date >= start_date and rec.date <= end_date)
                search_timetables = list(search_timetables)
        
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

                accountbalances = http.request.env['siantou.ems.core.teacher.hourly.rate'].sudo().search(search_domain, order=order)
                accountbalances = http.request.env['siantou.ems.core.hourly.rate'].sudo().search(search_domain, order=order)
                accountbalances = list(accountbalances)
                search_accountbalances = accountbalances

        _logger.info(f'----------- tototototototo search_accountbalances {search_accountbalances} -----------')

        return search_accountbalances, searchbar_inputs

    @staticmethod
    def notification(search='', search_in='all'):
        searchbar_inputs = {
            'all': {'label': 'Tout', 'input': 'all', 'domain': []},
        }
        if search_in not in searchbar_inputs.keys():
            search_in = 'all'
        search_domain = searchbar_inputs[search_in]['domain']

        order = 'date asc'

        search_notifications = []
        if http.request.env.user.employee_id.id:
            if http.request.env.user.employee_id.is_teacher:
                user = http.request.env.user.employee_id
                search_domain.append(('employee_id', '=', user.id))

                notifications = http.request.env['siantou.ems.timetable.notification'].sudo().search(search_domain, order=order)
                notifications = list(notifications)
                search_notifications = notifications

        _logger.info(f'----------- tototototototo search_notifications {search_notifications} -----------')

        return search_notifications, searchbar_inputs

    @staticmethod
    def is_float(data):
        try:
            float(data)
            return True
        except ValueError:
            return False

    @staticmethod
    def format_timetable(data, hours=[]):
        n = 0.0
        current_data = []
        current_hours = []
        timetables = {}
        df = {}

        for i in range(len(data)):
            data[i]['start_time'] = round(data[i]['start_time'], 2)
            data[i]['end_time'] = round(data[i]['end_time'], 2)

        if len(hours) > 0:
            for i in range(len(data)):
                for hour in hours:
                    if not (Helpers.increment_float_time(data[i]['start_time']) <= Helpers.increment_float_time(hour[0]) and Helpers.increment_float_time(data[i]['end_time']) > Helpers.increment_float_time(hour[0])) or not (Helpers.increment_float_time(data[i]['start_time']) < Helpers.increment_float_time(hour[1]) and Helpers.increment_float_time(data[i]['end_time']) >= Helpers.increment_float_time(hour[1])):
                        current_data.append(data[i])
                        break
                    else:
                        if not (Helpers.increment_float_time(data[i]['start_time']) == Helpers.increment_float_time(hour[0]) and Helpers.increment_float_time(data[i]['end_time']) == Helpers.increment_float_time(hour[1])):
                            if not (Helpers.increment_float_time(data[i]['start_time']) < Helpers.increment_float_time(hour[0]) and Helpers.increment_float_time(data[i]['end_time']) > Helpers.increment_float_time(hour[1])):
                                if Helpers.increment_float_time(data[i]['start_time']) == Helpers.increment_float_time(hour[0]):
                                    data[i]['start_time'] = hour[1]
                                    current_data.append(data[i])
                                    break
                                else:
                                    if Helpers.increment_float_time(data[i]['end_time']) == Helpers.increment_float_time(hour[1]):
                                        data[i]['end_time'] = hour[0]
                                        current_data.append(data[i])
                                        break
                            else:
                                data1 = copy.deepcopy(data[i])
                                data2 = copy.deepcopy(data[i])
                                data1['end_time'] = hour[0]
                                data2['start_time'] = hour[1]
                                current_data.append(data1)
                                current_data.append(data2)
                                break
            data = current_data

        data.sort(key=lambda d: d['date'])
        sorted_data = copy.deepcopy(data)

        for d in data:
            hours.append([d['start_time'], d['end_time']])

        for i, hour in enumerate(hours):
            if i == 0:
                n = hour[1] - hour[0]
            else:
                if n > hour[1] - hour[0]:
                    n = hour[1] - hour[0]

        n = round(n, 2)

        hours.sort(key=lambda h: h[0])

        for i in range(len(hours)):
            while Helpers.increment_float_time(hours[i][0]) < Helpers.increment_float_time(hours[i][1]):
                if Helpers.increment_float_time(hours[i][0], n) < Helpers.increment_float_time(hours[i][1]):
                    h = '{}-{}'.format(Helpers.increment_float_time(hours[i][0]), Helpers.increment_float_time(hours[i][0], n))
                else:
                    h = '{}-{}'.format(Helpers.increment_float_time(hours[i][0]), Helpers.increment_float_time(hours[i][1]))
                current_hours.append(h)
                hours[i][0] = Helpers.increment_float_time(hours[i][0], n)

        current_hours = list(set(current_hours))
        current_hours.sort(key=lambda h: float(h.split('-')[0]))

        for d in sorted_data:
            if d['date'].weekday() == 0:
                monday = d['date']
            else:
                monday = d['date'] - timedelta(days=d['date'].weekday())
            monday = datetime.strftime(monday, DATE_FORMAT)
            if not monday in timetables:
                timetables[monday] = {
                    'Heure': [hour for hour in current_hours],
                    'Lundi': [],
                    'Mardi': [],
                    'Mercredi': [],
                    'Jeudi': [],
                    'Vendredi': [],
                    'Samedi': [],
                    'Dimanche': [],
                }

                for i in range(len(timetables[monday]['Heure'])):
                    for key in timetables[monday].keys():
                        if key == 'Heure':
                            continue
                        timetables[monday][key].append(np.nan)
            if not monday in df:
                df[monday] = pd.DataFrame(timetables[monday], dtype=str)
            while Helpers.increment_float_time(d['start_time']) < Helpers.increment_float_time(d['end_time']):
                if Helpers.increment_float_time(d['start_time'], n) < Helpers.increment_float_time(d['end_time']):
                    h = '{}-{}'.format(Helpers.increment_float_time(d['start_time']), Helpers.increment_float_time(d['start_time'], n))
                else:
                    h = '{}-{}'.format(Helpers.increment_float_time(d['start_time']), Helpers.increment_float_time(d['end_time']))
                for i, row in df[monday].iterrows():
                    if h == timetables[monday]['Heure'][i]:
                        for j, column in enumerate(df[monday].columns):
                            for k, key in enumerate(timetables[monday].keys()):
                                if k == d['date'].weekday() + 1:
                                    if column == key:
                                        if Helpers.is_float(str(df[monday].loc[i, column])) and np.isnan(float(str(df[monday].loc[i, column]))):
                                            df[monday].loc[i, column] = str(d['id'])
                                        else:
                                            df[monday].loc[i, column] = '{}-{}'.format(df[monday].loc[i, column], str(d['id']))
                                    break
                d['start_time'] = Helpers.increment_float_time(d['start_time'], n)

        for monday in df.keys():
            df[monday].replace(np.nan, '-', inplace=True)

            for key in timetables[monday].keys():
                timetables[monday][key] = list(df[monday][key])
                if key != 'Heure':
                    for i, vals in enumerate(timetables[monday][key]):
                        timetables[monday][key][i] = []
                        if vals != '-':
                            for v in vals.split('-'):
                                timetables[monday][key][i].append([d for d in data if d['id'] == int(v)][0])

            monday = datetime.strptime(f'{monday}', DATE_FORMAT).date()
            saturday = monday + timedelta(days=5)
            monday_fr = datetime.strftime(monday, DATE_FORMAT_FR)
            saturday_fr = datetime.strftime(saturday, DATE_FORMAT_FR)
            monday = datetime.strftime(monday, DATE_FORMAT)
            saturday = '{} - {}'.format(monday_fr, saturday_fr)
            timetables[saturday] = timetables[monday]
            del(timetables[monday])

        _logger.info(f'----------- tototototototo timetables {timetables} -----------')

        return timetables

    @staticmethod
    def convert_datetime_from_utc(dt):
        new_tz = pytz.timezone('Africa/Douala')
        old_tz = pytz.utc
        local_dt = old_tz.localize(dt)
        dt = local_dt.astimezone(new_tz)
        return dt

    @staticmethod
    def convert_datetime_to_utc(dt):
        old_tz = pytz.timezone('Africa/Douala')
        new_tz = pytz.utc
        local_dt = old_tz.localize(dt)
        dt = local_dt.astimezone(new_tz)
        return dt

    @staticmethod
    def convert_float_to_time(tm, has_second=False):
        tm = str(tm)
        tm = tm.split('.')
        if len(tm[0]) == 1:
            tm[0] = '0{}'.format(tm[0])
        if len(tm[1]) == 1:
            tm[1] = '{}0'.format(tm[1])
        tm = ':'.join(tm)
        if has_second:
            tm = '{}:00'.format(tm)
        return tm

    @staticmethod
    def convert_time_to_float(tm):
        tm = str(tm)
        tm = tm.split(':')
        tm = tm[0:2]
        tm = '.'.join(tm)
        tm = eval(tm)
        tm = float(tm)
        tm = round(tm, 2)
        return tm

    @staticmethod
    def increment_float_time(tm, n=0.0):
        tm = str(tm)
        tm = tm.split('.')
        if len(tm[1]) == 1:
            tm[1] = '{}0'.format(tm[1])
        tm = time(int(tm[0]), int(tm[1]))
        n = str(n)
        n = n.split('.')
        if len(n[1]) == 1:
            n[1] = '{}0'.format(n[1])
        tm = datetime.combine(date.min, tm) + timedelta(hours=int(n[0]), minutes=int(n[1]))
        tm = datetime.strftime(tm, TIME_FORMAT_FR)
        tm = Helpers.convert_time_to_float(tm)
        return tm

    @staticmethod
    def paginate_calendar(items, page_size=10, page_number=1):
        if page_size == 0:
            page_size = 10
        keys = range(len(items.keys()))
        keys = list(keys)
        pages_total = [keys[i:i+page_size] for i in range(0, len(keys), page_size)]
        start_index = (page_number - 1) * page_size
        end_index = start_index + page_size
        pages = keys[start_index:end_index]
        data = {}
        for i, key in enumerate(items.keys()):
            if i in pages:
                data[key] = items[key]
        pages = data
        return {
            'total': len(items.keys()),
            'pages_total': len(pages_total),
            'pages': pages,
        }

    @staticmethod
    def paginate_list(items, page_size=10, page_number=1):
        if page_size == 0:
            page_size = 10
        pages_total = [items[i:i+page_size] for i in range(0, len(items), page_size)]
        start_index = (page_number - 1) * page_size
        end_index = start_index + page_size
        pages = items[start_index:end_index]
        return {
            'total': len(items),
            'pages_total': len(pages_total),
            'pages': pages,
        }

    @staticmethod
    def serialize_datetime(obj):
        if isinstance(obj, date):
            return datetime.strftime(obj, DATE_FORMAT_FR)
        elif isinstance(obj, datetime):
            return datetime.strftime(obj, DATETIME_FORMAT_FR)
        elif isinstance(obj, time):
            return datetime.strftime(obj, TIME_FORMAT_FR)
        else:
            return obj
