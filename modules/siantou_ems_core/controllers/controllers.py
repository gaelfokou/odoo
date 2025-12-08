# -*- coding: utf-8 -*-
from datetime import datetime
import random
import string
from odoo import http
import json
import base64
import logging
from odoo.exceptions import UserError, ValidationError
import requests

_logger = logging.getLogger(__name__)

class DeSchool(http.Controller):

    @http.route('/api/v1/niveaux', type="http", methods=['GET'], cors="*", website=True, auth="public")
    def list_niveaux(self, **kw):
        data = []
        niveaux = http.request.env['siantou.ems.core.level'].sudo().search([])
        for niv in niveaux:
            data.append({
                'id': niv.id,
                'name': niv.name,
            })

        return http.Response(
            json.dumps(data)
        )

    @http.route('/api/v1/pays', type="http", methods=['GET'], cors="*", website=True, auth="public")
    def list_country(self, **kw):
        data = []
        pays = http.request.env['siantou.ems.core.country'].sudo().search([])
        for p in pays:
            data.append({
                'id': p.id,
                'name': p.name,
            })

    @http.route('/api/v1/pays', type="http", methods=['GET'], cors="*", website=True, auth="public")
    def list_country(self, **kwargs):
        datas = []
        pays = http.request.env['siantou.ems.core.country'].sudo().search([])
        for p in pays:
            datas.append({
                'id': p.id,
                'name': p.name,
            })

        return http.Response(
            json.dumps(datas)
        )

    @http.route('/api/v1/pays/<int:id_country>/regions', type="http", methods=['GET'], cors="*", website=True, auth="public")
    def list_region_of_country(self, id_country):
        datas = []
        p = http.request.env['siantou.ems.core.country'].sudo().search([('id', '=', id_country)], limit=1)
        if len(p)>0:
            regions = http.request.env['siantou.ems.core.region'].sudo().search([('country_id', '=', p.id)])
            datas =[{'id':reg.id, 'name': reg.name} for reg in regions]

        return http.Response(
            json.dumps(datas)
        )

    @http.route('/api/v1/regions/<int:id_region>/cities', type="http", methods=['GET'], cors="*", website=True, auth="public")
    def list_cities_of_region(self, id_region):
        datas = []
        reg = http.request.env['siantou.ems.core.region'].sudo().search([('id', '=', id_region)], limit=1)
        if len(reg)>0:
            cities = http.request.env['siantou.ems.core.city'].sudo().search([('region_id', '=', reg.id)])
            datas=[{'id':city.id, 'name': city.name} for city in cities]

        return http.Response(
            json.dumps(datas)
        )

    @http.route('/api/v1/cities/<int:id_city>/quarters', type="http", methods=['GET'], cors="*", website=True, auth="public")
    def list_quarters_of_city(self, id_city):
        datas = []
        city = http.request.env['siantou.ems.core.city'].sudo().search([('id', '=', id_city)], limit=1)
        if len(city)>0:
            quarters = http.request.env['siantou.ems.core.quarter'].sudo().search([('city_id', '=', city.id)])
            datas=[{'id':quart.id, 'name': quart.name} for quart in quarters]

        return http.Response(
            json.dumps(datas)
        )

    @http.route('/api/v1/cycles', type="http", methods=['GET'], cors="*", website=True, auth="public")
    def list_courses(self, **kw):
        data = []
        cycles = http.request.env['oe.school.course'].sudo().search([])
        for cycle in cycles:
            filieres = http.request.env['siantou.ems.core.field_of_study'].sudo().search([('cycle_id', '=', cycle.id)])
            diplo_requis = http.request.env['oe.school.course.degree'].sudo().search([('cycle_id', '=', cycle.id)])

            if len(diplo_requis)>0:
                data.append({
                    'id': cycle.id,
                    'code': cycle.code,
                    'name': cycle.name,
                    'filieres': [{'id': filiere.id, 'name': filiere.name} for filiere in filieres],
                    'diplo_requis': [{'id': diplo.id, 'name': diplo.name} for diplo in diplo_requis]
                })

        return http.Response(
            json.dumps(data)
        )

    @http.route('/api/v1/<int:id>/etudiants', type="http", methods=['GET'], cors="*", website=True, auth="public")
    def get_etudiant_by_id(self, id,**kw):
        try:
            etudiant = http.request.env['oe.school.student.enrollment'].sudo().search([('id', '=', id)], limit=1)
            _logger.info(f'Étudiant: {etudiant}')
            if etudiant:
                return http.Response(
                    json.dumps({
                        'status': 'success',
                        'etudiant_id':etudiant.id,
                        'code_enrol':etudiant.code_enrol,
                        'diplo_requis_ids':[dipl.name for dipl in etudiant.diplo_requis_ids]
                    })
                )
            else:
                return http.Response(
                    json.dumps({
                        'status': 'error',
                        'data': f"Erreur lors de la recuperation de l'etudiant"
                    })
                )
        except Exception as e:
            return http.Response(
                json.dumps({
                    'status': 'error',
                    'data': f"{e.args}"
                })
            )

    def generate_code(self):
        # Get the current year
        current_year = datetime.now().year
        # Generate two random alphabet letters
        letters = ''.join(random.choices(string.ascii_uppercase, k=2))
        student_enroll = http.request.env['oe.school.student.enrollment'].sudo().search([])
        # Combine year and letters
        nbre = len(student_enroll) + 1
        code = f"{current_year}{letters}0000{nbre}"
        return code

    @http.route('/api/v1/save', type="http", methods=['POST'], cors="*", website=True, auth="public")
    def admission_form_submit(self,):
        _logger.info(request.httprequest.data)
        data = json.loads(request.httprequest.data)
        is_existing = True

        # _logger.info(type(int(data.get('field_of_study_id'))))

        try:
            #=== Get matricule generated
            code_enrol = self.generate_code()
            while is_existing:
                etudiant = http.request.env['oe.school.student.enrollment'].sudo().search(
                    [('code_enrol', '=', code_enrol)],
                    limit=1
                )
                if not etudiant:
                    data['code_enrol'] = code_enrol
                    is_existing = False

            #===== create res partner instance =================
            partner = http.request.env['res.partner'].sudo().create({
                "name":data['name']
            })

            _logger.info(partner.name)
            #=== Create a new student
            data['partner_id'] = partner.id

            #=== Create a new student
            etudiant = http.request.env['oe.school.student.enrollment'].sudo().create(data)

            if etudiant:
                return http.Response(
                    json.dumps({
                        'status': 'success',
                        'etudiant_id':etudiant.id,
                    })
                )
        except Exception as e:
            return http.Response(
                json.dumps({
                    'status': 'error',
                    'data':f"{e.args}"
                })
            )

