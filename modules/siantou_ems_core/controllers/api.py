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

    @http.route(['/api/v1/niveaux'], type="http", methods=['GET'], cors="*", auth="none")
    def list_niveaux(self, **kw):
        data = []
        niveaux = request.env['siantou.ems.core.level'].sudo().search([])
        for niv in niveaux:
            data.append({
                'id': niv.id,
                'name': niv.name,
            })

        return Response(
            json.dumps(data)
        )



    @http.route('/api/v1/pays', type="http", methods=['GET'], cors="*", auth="none")
    def list_country(self, **kwargs):
        datas = []
        pays = request.env['siantou.ems.core.country'].sudo().search([])
        for p in pays:
            datas.append({
                'id': p.id,
                'name': p.name,
            })


        return Response(
            json.dumps(datas)
        )

    @http.route('/api/v1/pays/<int:id_country>/regions', type="http", methods=['GET'], cors="*", auth="none")
    def list_region_of_country(self, id_country):
        datas = []
        p = request.env['siantou.ems.core.country'].sudo().search([('id', '=', id_country)], limit=1)
        if len(p)>0:
            regions = request.env['siantou.ems.core.region'].sudo().search([('country_id', '=', p.id)])
            datas =[{'id':reg.id, 'name': reg.name} for reg in regions]


        return Response(
            json.dumps(datas)
        )

    @http.route('/api/v1/regions/<int:id_region>/cities', type="http", methods=['GET'], cors="*", auth="none")
    def list_cities_of_region(self, id_region):
        datas = []
        region_id = request.env['siantou.ems.core.region'].sudo().search([('id','=',id_region)], limit=1)
        if region_id:
            cities = request.env['siantou.ems.core.city'].sudo().search([('region_id', '=', region_id.id)])
            datas=[{'id':city.id, 'name': city.name} for city in cities]

        return Response(
            json.dumps(datas)
        )

    @http.route('/api/v1/cities/<int:id_city>/quarters', type="http", methods=['GET'], cors="*", auth="none")
    def list_quarters_of_city(self, id_city):
        datas = []
        city = request.env['siantou.ems.core.city'].sudo().search([('id', '=', id_city)], limit=1)
        if len(city)>0:
            quarters = request.env['siantou.ems.core.quarter'].sudo().search([('city_id', '=', city.id)])
            datas=[{'id':quart.id, 'name': quart.name} for quart in quarters]

        return Response(
            json.dumps(datas)
        )

    
    @http.route('/api/v1/cycles', type="http", methods=['GET'], cors="*", auth="none")
    def list_courses(self, **kw):
        data = []
        cycles = []
        year_id = request.env['siantou.ems.core.year'].sudo().search(
            [('active', '=',True),], 
            limit=1
        )

        #=== récupération de la session d'admission active de l'année active
        session_ids = request.env['siantou.session'].sudo().search(
            [
                ('active', '=', True),
                ('year_id', '=', year_id.id),
            ]
        )
        for session_id in session_ids:
            for cycle_id in session_id.cycle_ids:
                # cycle_id = request.env['oe.school.course'].sudo().search([('id','=',id)], limit=1)
                cycles.append(cycle_id)
                

        # cycles = request.env['oe.school.course'].sudo().search([])
        for cycle in cycles:
            filieres = request.env['siantou.ems.core.field_of_study'].sudo().search([('cursus_id', '=', cycle.id)])
            diplo_requis = request.env['oe.school.course.degree'].sudo().search([('cursus_id', '=', cycle.id)])

            if len(diplo_requis)>0 and len(filieres)>0:
                data.append({
                    'id': cycle.id,
                    'code': cycle.code,
                    'name': cycle.name,
                    'filieres': [{'id': filiere.id, 'name': filiere.name} for filiere in filieres],
                    'diplo_requis': [{'id': diplo.id, 'name': diplo.name} for diplo in diplo_requis]
                })


        return Response(
            json.dumps(data)
        )



    @http.route('/api/v1/<int:id>/etudiants', type="http", methods=['GET'], cors="*", auth="none")
    def get_etudiant_by_id(self, id,**kw):
        try:
            etudiant = request.env['oe.school.student.enrollment'].sudo().search([('id', '=', id)], limit=1)
            code_bank_paie_frais = request.env['siantou.ems.fee.config.bank'].sudo().search([('active', '=', True)], limit=1)
            _logger.info(f'Etudiant: {etudiant}')
            _logger.info(f'numero: {code_bank_paie_frais.numero}')
            if etudiant:
                return Response(
                    json.dumps({
                        'status': 'success',
                        'etudiant_id':etudiant.id,
                        'code_enrol':etudiant.code_enrol,
                        'code_bank_paie_frais':code_bank_paie_frais.numero,
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

            




    @http.route('/api/v1/save', type="http", methods=['POST'], cors="*", auth="none", csrf=False)
    def admission_form_submit(self,):
        # _logger.info(request.httprequest.data)
        data = json.loads(request.httprequest.data)
        is_existing = True

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

            year_id = request.env['siantou.ems.core.year'].sudo().search(
                [('active', '=',True),], 
                limit=1
            )

            #=== récupération de la session d'admission active
            session_id = request.env['siantou.session'].sudo().search(
                [
                    ('active', '=', True),
                    ('year_id', '=', year_id.id),
                    ('cycle_ids', 'in', int(data['cycle_id'])),
                ], 
                limit=1
            )

            _logger.info(session_id)
            # _logger.info(session_id.cycle_ids)
            # on Vérifie si le cycle choisi par l'étudion est dans la session d'admission active
            is_present = session_id.cycle_ids.filtered(lambda cycle: cycle.id == int(data['cycle_id']))
            if session_id and bool(is_present):
                _logger.info(is_present)
                _logger.info(session_id.cycle_ids)
                #=== récupération du régistre de la session d'admission active et correspondant au cycle choisi par l'utilisateur
                registre_id = request.env['siantou.session.registre'].sudo().search(
                    [
                        ('session_id', '=', session_id.id), 
                        ('cycle_id', '=', int(data['cycle_id']))
                    ],
                    limit=1
                )
                _logger.info(registre_id)
                if registre_id:

                    #=== Insertion de l'utilisateur dans le registre correspondant à son cycle
                    data['registre_id']=registre_id.id
                    _logger.info("========= etudiant pas encore crée")
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
                else:
                    return Response(
                            json.dumps({
                                'status': 'error',
                                'data':"Aucune session d'admission ouverte pour le cycle choisi",
                            })
                        )
            else:
                return Response(
                        json.dumps({
                            'status': 'error',
                            'data':"Aucune session d'admission ouverte pour le cycle choisi",
                        })
                    )
        except Exception as e:
            return Response(
                json.dumps({
                    'status': 'error',
                    'data':f"{e.args}"
                })
            )






