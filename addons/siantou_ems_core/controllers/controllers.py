# -*- coding: utf-8 -*-
from odoo import http
import json
import base64
import logging
from odoo.http import request, content_disposition, Response
from odoo.exceptions import ValidationError  # Import the ValidationError class


_logger = logging.getLogger("++++++++++++")

class DeSchool(http.Controller):
    # @http.route('/de_school/de_school/',type="json", auth='public')
    # def index(self, **kw):
    #     return "Hello, world"
    


    @http.route('/api/v1/cycles', type="http", auth='public', methods=['GET'], csrf=False, cors="*")
    def list_courses(self, **kw):
        data = []
        cycles = request.env['oe.school.course'].sudo().search([])
        for cycle in cycles:
            filieres = request.env['siantou.ems.core.field_of_study'].sudo().search([('cursus_id', '=', cycle.id)])
            data.append({
                'id': cycle.id,
                'code': cycle.code,
                'name': cycle.name,
                'filieres': [{'id': filiere.id, 'name': filiere.name} for filiere in filieres]
            })
        # _logger.info(f'Cycle: {cycle}')

        return Response(
            json.dumps(data)
        )


    @http.route('/api/v1/<int:id>/etudiants', type="http", auth='public', methods=['GET'], csrf=False, cors="*")
    def get_etudiant_by_id(self, **kw):
        etudiant = request.env['oe.school.student.enrollment'].sudo().search([('id', '=', id)], limit=1)
        _logger.info(f'Etudiant: {etudiant}')
        return Response(
            json.dumps({
                'id': etudiant.id,
                'full_name': etudiant.full_name,
                'matricule': etudiant.matricule,
            })
        )


    @http.route('/api/v1/save', type="http", auth='public', methods=['POST'], csrf=False, cors="*")
    def admission_form_submit(self,):
        # _logger.info(request.httprequest.data)
        data = json.loads(request.httprequest.data)
        _logger.info(type(int(data.get('specialite_id'))))
        try:
            etudiant = request.env['oe.school.student.enrollment'].sudo().create({
                'full_name': data.get('full_name'),
                'matricule': data.get('matricule'),
                'cycle_id': int(data.get('cycle_id')),
                'specialite_id': int(data.get('specialite_id')),
                'type_cour': data.get('type_cour'),
                'status_univ': data.get('status_univ'),
                'nbre_matiere': data.get('nbre_matiere'),
                'date_naissance': data.get('date_naissance'),
                'lieu_naissance': data.get('lieu_naissance'),
                'sexe': data.get('sexe'),
                'situat_matri': data.get('situat_matri'),
                'nationalite': data.get('nationalite'),
                'lieu_residence': data.get('lieu_residence'),
                'email': data.get('email'),
                'num_tel': data.get('num_tel'),
                'dipl_req': data.get('dipl_req'),
                'session_lieu_obt': data.get('session_lieu_obt'),
                'dern_etab_freq': data.get('dern_etab_freq'),
                'annee_acad': data.get('annee_acad'),
                'niveau': data.get('niveau'),
                'full_name_tutor': data.get('full_name_tutor'),
                'num_tel_tutor': data.get('num_tel_tutor'),
            })
            if etudiant:
                _logger.info(etudiant)
                return Response(
                    json.dumps({
                        'status': 'success',
                        'etudiant':etudiant.id
                    })
                )
        except Exception as e:
            return Response(
                json.dumps({
                    'status': 'failure',
                    'data':f"{e.args}"
                })
            )



