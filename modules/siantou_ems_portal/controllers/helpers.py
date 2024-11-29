# helpers.py
from odoo import http
from odoo.addons.portal.controllers import portal
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class Helpers:
    @staticmethod
    def timetable(search=None, search_in='all', sortby=None):
        if not search:
            search = ''
        searchbar_inputs = {
            'all': {'label': 'Tout', 'input': 'all', 'domain': []},
            'filiere': {'label': 'Filière', 'input': 'filiere', 'domain': [('field_of_study_id.name', 'like', search)]},
            'cours': {'label': 'Cours', 'input': 'cours', 'domain': [('subject_id.name', 'like', search)]},
            'enseignant': {'label': 'Enseignant', 'input': 'enseignant', 'domain': [('employee_id.name', 'like', search)]},
            'filiere': {'label': 'Filière', 'input': 'filiere', 'domain': [('field_of_study_id.name', 'like', search)]},
            'niveau': {'label': 'Niveau', 'input': 'niveau', 'domain': [('level_id.name', 'like', search)]},
            'cycle': {'label': 'Cycle', 'input': 'cycle', 'domain': [('cycle_id.name', 'like', search)]},
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
            search_domain.append(('employee_id', '=', user.id))
        else:
            user = http.request.env.user
            # Chercher l'étudiant en fonction de l'ID de l'utilisateur (user_id)
            student = http.request.env['oe.school.student'].sudo().search([('user_id', '=', user.id)], limit=1)
            if student:
                # Si l'étudiant est trouvé, on filtre par cycle, niveau et filière
                search_domain.append(('level_id', '=', student.level_id.id))
                search_domain.append(('field_of_study_id', '=', student.field_of_study_id.id))

        search_timetables = http.request.env['siantou.ems.timetable.timetable'].sudo().search(search_domain, order=order)

        _logger.info(f'----------- tototototototo search_timetables {search_timetables} -----------')

        
        return search_timetables, searchbar_inputs, search_in, sortby, searchbar_sortings

    @staticmethod
    def schoolfee(search=None, search_in='all', sortby=None):
        if not search:
            search = ''
        searchbar_inputs = {
            'all': {'label': 'Tout', 'input': 'all', 'domain': []},
        }
        if search_in not in searchbar_inputs.keys():
            search_in = 'all'
        search_domain = searchbar_inputs[search_in]['domain']

        searchbar_sortings = {
            'date-desc': {'label': 'Date desc', 'order': 'date_payment desc'},
            'date-asc': {'label': 'Date asc', 'order': 'date_payment asc'},
        }
        if not sortby or sortby not in searchbar_sortings.keys():
            sortby = 'date-desc'
        order = searchbar_sortings[sortby]['order']

        # Chercher l'étudiant en fonction de l'ID de l'utilisateur (user_id)
        student = http.request.env['oe.school.student'].sudo().search([('user_id', '=', user.id)], limit=1)
        if student:
            # Si l'étudiant est trouvé, on filtre par cycle, niveau et filière
            search_domain.append(('student_id', '=', student.id))

        search_schoolfees = http.request.env['education.fee.payment'].sudo().search(search_domain, order=order)

        _logger.info(f'----------- tototototototo search_schoolfees {search_schoolfees} -----------')

        
        return search_schoolfees, searchbar_inputs, search_in, sortby, searchbar_sortings
