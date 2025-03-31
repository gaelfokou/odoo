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

_logger = logging.getLogger(__name__)

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
                'code': p.code,
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
        _logger.info(session_ids)
        if session_ids:
            for session_id in session_ids:
                for cycle_id in session_id.cycle_ids:
                    cycles.append(cycle_id)

        _logger.info(cycles)   
        if cycles:
            for cycle in cycles:
                niveaux = cycle.level_ids
                filieres = request.env['siantou.ems.core.field_of_study'].sudo().search([('cycle_id', '=', cycle.id)])
                diplo_requis = request.env['oe.school.course.degree'].sudo().search([('cycle_id', '=', cycle.id)])

                if len(diplo_requis)>0 and len(filieres)>0 and len(niveaux)>0:
                    data.append({
                        'id': cycle.id,
                        'code': cycle.code,
                        'name': cycle.name,
                        'filieres': [{'id': filiere.id, 'name': filiere.name} for filiere in filieres],
                        'niveaux': [{'id': niv.id, 'name': niv.name} for niv in niveaux],
                        'diplo_requis': [{'id': diplo.id, 'name': diplo.name} for diplo in diplo_requis]
                    })

        _logger.info(data) 

        return Response(
            json.dumps(data)
        )

    @http.route('/api/v1/filieres/<int:id>/specialites', type="http", methods=['GET'], cors="*", auth="none")
    def list_specialites_of_filiere(self, id):
        datas = []
        field_of_study_id = request.env['siantou.ems.core.field_of_study'].sudo().search([('id', '=', id)], limit=1)
        if field_of_study_id:
            options = request.env['siantou.ems.core.specialty'].sudo().search([('field_of_study_id', '=', field_of_study_id.id)])
            datas=[{'id':opt.id, 'name': opt.name} for opt in options]
        _logger.info(datas)
        return Response(
            json.dumps(datas)
        )

    @http.route('/api/v1/<int:id>/etudiants', type="http", methods=['GET'], cors="*", auth="none")
    def get_etudiant_by_id(self, id,**kw):
        try:
            etudiant = request.env['oe.school.student.enrollment'].sudo().search([('id', '=', id)], limit=1)
            code_bank_paie_frais = request.env['siantou.ems.fee.config.bank'].sudo().search([('active', '=', True)], limit=1)
            _logger.info(f'Étudiant: {etudiant}')
            _logger.info(f'numero: {code_bank_paie_frais.numero}')
            if etudiant:
                return Response(
                    json.dumps({
                        'status': 'success',
                        'etudiant_id':etudiant.id,
                        'code_enrol':etudiant.code_enrol,
                        'info_banque':{
                            'denomination':code_bank_paie_frais.denomination if code_bank_paie_frais else '---',
                            'numero':code_bank_paie_frais.numero if code_bank_paie_frais else '---',
                            'nom_bank':code_bank_paie_frais.nom_bank if code_bank_paie_frais else '---',
                            'code_1':code_bank_paie_frais.code_1 if code_bank_paie_frais else '---',
                            'code_2':code_bank_paie_frais.code_2 if code_bank_paie_frais else '---',
                            'cle_rib':code_bank_paie_frais.cle_rib if code_bank_paie_frais else '---',
                            'swift_code':code_bank_paie_frais.swift_code if code_bank_paie_frais else '---',
                            'iban':code_bank_paie_frais.iban if code_bank_paie_frais else '---',
                        },
                        'diplo_requis_ids':[dipl.name for dipl in etudiant.diplo_requis_ids]
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

    def create_enroll_document(self, candidat, file):
        # Création des document pour chaque candidature
        document_obj = request.env['oe.school.student.enrollment.file']

        if file:
            dmd_id = document_obj.create({
                "student_enrollemnt_id": candidat.id,
            })
            file_dmd = file
            mime_type = file_dmd.content_type
            attachment_id = request.env['ir.attachment'].sudo().create({
                'name': "%s-CANDIDAT-%s" % (candidat.code_enrol),
                'type': 'binary',
                'datas': base64.b64encode(file_dmd.read()),
                'store_fname': "%s-CANDIDAT-%s" % (candidat.code_enrol),
                'res_model': dmd_id._name,
                'res_id': dmd_id.id,
                'mimetype': mime_type
            })
            dmd_id.update({
                'doc_attachment_id':[(4, attachment_id.id)]
            })

            return dmd_id
        else:
            return 0

    @http.route('/api/v1/etudiants/<int:id>/upload/docs', type="http", methods=['post'], cors="*", auth="none", csrf=False)
    def upload_doc_etudiant_by_id(self, id,**kw):
        documents = []
        try:
            etudiant = request.env['oe.school.student.enrollment'].sudo().search([('id', '=', id)], limit=1)
            _logger.info(f'Étudiant: {etudiant}')

            files = request.httprequest.files.getlist('file')
            _logger.info(request.httprequest.files)
            _logger.info(files)
            if etudiant:
                if files:
                    for file in files:
                        _logger.info(file.filename)
                        file_name = file.filename
                        attachment_id = request.env['ir.attachment'].sudo().create({
                            'name': file_name,
                            'type': 'binary',
                            'datas': base64.b64encode(file.read()),
                            'res_model': etudiant._name,
                            'res_id': etudiant.id,
                        })
                        etudiant.update({
                            'file_ids':[(4, attachment_id.id)]
                        })
                        # dmd_id = self.create_enroll_document(
                        #     etudiant,
                        #     base64.b64decode(file)
                        # )

                #         documents.append(dmd_id.id)
                # _logger.info(documents)
                # etudiant.files_ids = [(6, 0, documents)]
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
                        'data': f"Erreur lors de la savegarde des documents"
                    })
                )
        except Exception as e:
            return Response(
                json.dumps({
                    'status': 'error',
                    'data': f"{e.args}"
                })
            )

    @http.route('/api/v1/save', type="http", methods=['POST'], cors="*", auth="none", csrf=False)
    def admission_form_submit(self,**kwargs):
        data = json.loads(request.httprequest.data)
        _logger.info(data)
        is_existing = True

        try:

            first_name = data.pop('first_name')
            last_name = data.pop('last_name')
            data['name'] = f"{first_name} {last_name}"
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
            # partner = request.env['res.partner'].sudo().create({
            #     "name":data['name']
            # })

            # _logger.info(partner.name)
            #=== Create a new student
            # data['partner_id'] = partner.id

            year_id = request.env['siantou.ems.core.year'].sudo().search(
                [('active', '=',True),],
                limit=1
            )

            #=== récupération de la session d'admission active
            session_id = request.env['siantou.session'].sudo().search(
                [
                    ('state', '=', 'admission'),
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
                    # documents = []
                    _logger.info("========= etudiant pas encore crée")

                    # file_name = kwargs.get('filename')
                    #=== Create a new student
                    if not data['nationalite']:
                        data['is_autre_pays'] = True
                    else:
                        data['is_autre_pays'] = False
                    etudiant = request.env['oe.school.student.enrollment'].sudo().create(data)
                    # _logger.info(files)

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

