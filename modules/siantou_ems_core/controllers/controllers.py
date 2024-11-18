# -*- coding: utf-8 -*-
from datetime import datetime
import random
import string
from odoo import http
import json
import base64
import logging
from odoo.http import request, content_disposition, Response
from odoo.exceptions import ValidationError  # Import the ValidationError class
import requests

_logger = logging.getLogger("++++++++++++")

class DeSchool(http.Controller):

    @http.route('/api/v1/niveaux', type="http", auth='none', methods=['GET'], csrf=False, cors="*")
    def list_niveaux(self, **kw):
        data = []
        niveaux = request.env['siantou.ems.core.level'].sudo().search([])
        for niv in niveaux:
            data.append({
                'id': niv.id,
                'name': niv.name,
            })

        _logger.info(f'Niveaux: {data}')

        return Response(
            json.dumps(data)
        )

    @http.route('/api/v1/pays', type="http", auth='none', methods=['GET'], csrf=False, cors="*")
    def list_country(self, **kw):
        data = []
        pays = request.env['siantou.ems.core.country'].sudo().search([])
        for p in pays:
            data.append({
                'id': p.id,
                'name': p.name,
            })

        _logger.info(f'Pays: {data}')


    @http.route('/api/v1/pays', type="http", auth='none', methods=['GET'], csrf=False, cors="*")
    def list_country(self, **kwargs):
        datas = []
        pays = request.env['siantou.ems.core.country'].sudo().search([])
        for p in pays:
            datas.append({
                'id': p.id,
                'name': p.name,
            })

        _logger.info(f'datass : {datas}')

        return Response(
            json.dumps(datas)
        )

    @http.route('/api/v1/pays/<int:id_country>/regions', type="http", auth='none', methods=['GET'], csrf=False, cors="*")
    def list_region_of_country(self, id_country):
        datas = []
        p = request.env['siantou.ems.core.country'].sudo().search([('id', '=', id_country)], limit=1)
        if len(p)>0:
            regions = request.env['siantou.ems.core.region'].sudo().search([('country_id', '=', p.id)])
            datas =[{'id':reg.id, 'name': reg.name} for reg in regions]

        _logger.info(f'datass : {datas}')

        return Response(
            json.dumps(datas)
        )


    @http.route('/api/v1/regions/<int:id_region>/cities', type="http", auth='none', methods=['GET'], csrf=False, cors="*")
    def list_cities_of_region(self, id_region):
        datas = []
        reg = request.env['siantou.ems.core.region'].sudo().search([('id', '=', id_region)], limit=1)
        if len(reg)>0:
            cities = request.env['siantou.ems.core.city'].sudo().search([('region_id', '=', reg.id)])
            datas=[{'id':city.id, 'name': city.name} for city in cities]

        _logger.info(f'Datas : {datas}')
        return Response(
            json.dumps(datas)
        )


    @http.route('/api/v1/cities/<int:id_city>/quarters', type="http", auth='none', methods=['GET'], csrf=False, cors="*")
    def list_quarters_of_city(self, id_city):
        datas = []
        city = request.env['siantou.ems.core.city'].sudo().search([('id', '=', id_city)], limit=1)
        if len(city)>0:
            quarters = request.env['siantou.ems.core.quarter'].sudo().search([('city_id', '=', city.id)])
            datas=[{'id':quart.id, 'name': quart.name} for quart in quarters]

        _logger.info(f'datass : {datas}')
        return Response(
            json.dumps(datas)
        )
        return Response(
            json.dumps(data)
        )
    
    @http.route('/api/v1/cycles', type="http", auth='none', methods=['GET'], csrf=False, cors="*")
    def list_courses(self, **kw):
        data = []
        cycles = request.env['oe.school.course'].sudo().search([])
        for cycle in cycles:
            filieres = request.env['siantou.ems.core.field_of_study'].sudo().search([('cursus_id', '=', cycle.id)])
            diplo_requis = request.env['oe.school.course.degree'].sudo().search([('cursus_id', '=', cycle.id)])

            if len(diplo_requis)>0:
                data.append({
                    'id': cycle.id,
                    'code': cycle.code,
                    'name': cycle.name,
                    'filieres': [{'id': filiere.id, 'name': filiere.name} for filiere in filieres],
                    'diplo_requis': [{'id': diplo.id, 'name': diplo.name} for diplo in diplo_requis]
                })

        _logger.info(f'Cycles: {data}')

        return Response(
            json.dumps(data)
        )



    @http.route('/api/v1/<int:id>/etudiants', type="http", auth='none', methods=['GET'], csrf=False, cors="*")
    def get_etudiant_by_id(self, id,**kw):
        try:
            etudiant = request.env['oe.school.student.enrollment'].sudo().search([('id', '=', id)], limit=1)
            _logger.info(f'Etudiant: {etudiant}')
            if etudiant:
                return Response(
                    json.dumps({
                        'status': 'success',
                        'etudiant_id':etudiant.id,
                        'code_enrol':etudiant.code_enrol,
                        'dipl_req_ids':[dipl.name for dipl in etudiant.dipl_req_ids]
                    })
                )
            else:
                return Response(
                    json.dumps({
                        'status': 'error',
                        'data': f"Erreur lors de la recuperation de l'etudiant"
                    })
                )
        except Exception as e:
            return Response(
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
        student_enroll = request.env['oe.school.student.enrollment'].sudo().search([])
        # Combine year and letters
        nbre = len(student_enroll) + 1
        code = f"{current_year}{letters}0000{nbre}"
        return code


    @http.route('/api/v1/save', type="http", auth='none', methods=['POST'], csrf=False, cors="*")
    def admission_form_submit(self,):
        _logger.info(request.httprequest.data)
        data = json.loads(request.httprequest.data)
        is_existing = True

        # _logger.info(type(int(data.get('field_of_study_id'))))

        try:
            #=== Get matricule generated
            code_enrol = self.generate_code()
            while is_existing:
                etudiant = request.env['oe.school.student.enrollment'].sudo().search(
                    [('code_enrol', '=', code_enrol)], 
                    limit=1
                )
                if not etudiant:
                    data['code_enrol'] = code_enrol
                    is_existing = False

            #===== create res partner instance =================
            partner = request.env['res.partner'].sudo().create({
                "name":data['name']
            })
            
            _logger.info(partner.name)
            #=== Create a new student
            data['partner_id'] = partner.id

            #=== Create a new student
            etudiant = request.env['oe.school.student.enrollment'].sudo().create(data)

            if etudiant:
                _logger.info(etudiant)
                return Response(
                    json.dumps({
                        'status': 'success',
                        'etudiant_id':etudiant.id,
                    })
                )
        except Exception as e:
            return Response(
                json.dumps({
                    'status': 'error',
                    'data':f"{e.args}"
                })
            )



