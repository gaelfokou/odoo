# -*- coding: utf-8 -*-
from datetime import datetime
import random
import string
from odoo import http
import json
from odoo.exceptions import UserError, ValidationError
import requests
from odoo.tools import formatLang

import base64
import os


import logging
_logger = logging.getLogger(__name__)




class DeSchool(http.Controller):

    @http.route('/qrcode/<int:stm_line_id>/<int:partner_id>/details', type="http", methods=['GET'], website=True, auth="public")
    def qrcode_etudiant_details(self, stm_line_id, partner_id):
        amount_total_recu = 0
        amount_total_restant = 0
        is_moratoire = False
        data = {}
        now = datetime.now()
        date_str = now.strftime("%d/%m/%Y à %H:%M:%S") 
        # _logger.info(f"============ stm_line_id :: {stm_line_id}")
        # _logger.info(f"============ partner_id :: {partner_id}")

        stm_line_obj = http.request.env['account.bank.statement.line'].sudo().search([
                ('id', '=', stm_line_id)
            ],
            limit=1
        )
        # _logger.info(f"============ stm_line_obj :: {stm_line_obj}")
        enrollement = http.request.env['oe.school.student'].sudo().search([('partner_id', '=', partner_id)], limit=1)
        annee_academique = enrollement.year_id
        if not enrollement.year_id:
            annee_academique = stm_line_obj._get_annee_academique_courante()
        
        data['info_etudiant'] = {
            'nom': enrollement.partner_id.display_name,
            'specialite': "%s" % (enrollement.class_id.name),
            'matricule': enrollement.matricule,
            'niveau': enrollement.level_id.name,
            'ecole': enrollement.school_id.name,
            'cycle': enrollement.cycle_id.name,
        }
        
        date = stm_line_obj.date 
        if date and date==now.date():
            date = date.strftime("%d/%m/%Y")
        else:
            date = now.date().strftime("%d/%m/%Y")
        data['info_entete'] = {
            'caissier': stm_line_obj.caissier_id.name,
            'today_date': date_str,
            'anne_academique': annee_academique.name,
            'date': date,
            'numero_recu': stm_line_obj.move_id.name,
            # 'logo':image_data,
            'montant_verse': formatLang(http.request.env, stm_line_obj.amount, currency_obj=stm_line_obj.currency_id),
        }

        data['lignes_de_recouvrements'] = []
        redevances_paiement_partiel_ou_total = http.request.env['account.move'].sudo().search([
                ('move_type', '=', 'out_invoice'), 
                ('partner_id', '=', stm_line_obj.partner_id.id),
                ('payment_state', 'in', ['paid', 'partial'])
            ], 
            order='invoice_date_due ASC, id ASC'
        ) 
        redevances_non_payees = http.request.env['account.move'].sudo().search([
            ('move_type', '=', 'out_invoice'),
            ('partner_id', '=', stm_line_obj.partner_id.id),
            ('state', '=', 'posted'),
            ('payment_state', '=', 'not_paid')
        ])
        # if redevances_paiement_partiel_ou_total or redevances_non_payees:
        moratoire_line_ids = http.request.env['siantou.ems.fee.moratoire.line'].sudo().search([
                ('moratoire_id.student_id.partner_id', '=', stm_line_obj.partner_id.id),
                ('state', '=', 'validate')
            ]
        ) 
        # _logger.info(f"======= redevances_paiement_partiel_ou_total :: {redevances_paiement_partiel_ou_total}")
        for redevance in redevances_paiement_partiel_ou_total:
            # if not redevance.invoice_payments_widget:
            #     continue
            if redevance.ref:
                info_sur_paiements = redevance.invoice_payments_widget['content']
                amount = 0
                for info in info_sur_paiements:
                    amount +=info['amount']
                info_ligne = {
                    'code': redevance.name,
                    'libelle': redevance.ref,
                    'montant_recu': f"{float(amount)}  FCFA",
                    'observation': [{'date':info['date'].strftime("%d/%m/%Y"),'montant_recu':info['amount_company_currency']} for info in info_sur_paiements],
                }
                amount_total_recu += amount
                for moratoire_line_id in moratoire_line_ids:
                    if redevance.id in moratoire_line_id.move_ids.ids:
                        if moratoire_line_id.date_echeance >= now.date():
                            is_moratoire = True
                            info_ligne['moratoire'] = moratoire_line_id.date_echeance.strftime("%d/%m/%Y")
                
                amount_total_restant += redevance.amount_residual
                data['lignes_de_recouvrements'].append(info_ligne)


        
        for redevance in redevances_non_payees:
            if redevance.ref:
                amount_total_restant += redevance.amount_residual
                for moratoire_line_id in moratoire_line_ids:
                    if redevance.id in moratoire_line_id.move_ids.ids:
                        if moratoire_line_id.date_echeance >= now.date():
                            is_moratoire = True
                            info_ligne = {
                                'code': redevance.name,
                                'libelle': redevance.ref,
                                'montant_recu': formatLang(http.request.env, 0, currency_obj=stm_line_obj.currency_id),
                                'observation': [],
                            }
                            info_ligne['moratoire'] = moratoire_line_id.date_echeance.strftime("%d/%m/%Y")
                            data['lignes_de_recouvrements'].append(info_ligne)
        
        data['amount_total_recu'] = f"{amount_total_recu}  FCFA"
        data['amount_total_restant'] = f"{amount_total_restant} FCFA"

        return http.request.render('siantou_ems_core.render_recu_payment',{'data':data})


    @http.route('/api/v1/pays', type="http", methods=['GET'], cors="*", website=True, auth="public")
    def list_country(self, **kwargs):
        datas = []
        pays = http.request.env['siantou.ems.core.country'].sudo().search([])
        for p in pays:
            datas.append({
                'id': p.id,
                'code': p.code,
                'name': p.name,
            })

        return http.Response(
            json.dumps(datas)
        )


    @http.route('/api/v1/years', type="http", methods=['GET'], cors="*", website=True, auth="public")
    def list_years(self, **kwargs):
        data = []
        years = http.request.env['siantou.ems.core.year'].sudo().search([('is_active', '=', False)])
        # _logger.info(f"=========== API years :: {years}")
        for year in years:
            data.append({
                'id': year.id,
                'name': year.name,
            })
        # _logger.info(f"=========== API years :: {data}")
        if data:
            return http.Response(
                json.dumps({
                    'status': 200,
                    "message": "Données récupérées avec succès",
                    'data':data,
                })
            )
        else:
            return http.Response(
                json.dumps({
                    'status': 500,
                    "code": "SERVER_ERROR",
                    "message": "Erreur interne du serveur.",
                    'details':"Aucune année académique disponible",
                })
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
        region_id = http.request.env['siantou.ems.core.region'].sudo().search([('id', '=', id_region)], limit=1)
        if region_id:
            cities = http.request.env['siantou.ems.core.city'].sudo().search([('region_id', '=', region_id.id)])
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
        cycles = []
        year_id = http.request.env['siantou.ems.core.year'].sudo().search(
            [('is_active', '=', True),],
            limit=1
        )

        #=== récupération de la session d'admission active de l'année active
        session_ids = http.request.env['siantou.session'].sudo().search(
            [
                ('is_active', '=', True),
                ('year_id', '=', year_id.id),
            ]
        )
        # _logger.info(session_ids)
        if session_ids:
            for session_id in session_ids:
                for cycle_id in session_id.cycle_ids:
                    cycles.append(cycle_id)

        # _logger.info(f"=========== API cycles :: {cycles}")   
        if cycles:
            for cycle in cycles:
                level_ids = cycle.level_ids
                specialty_ids = http.request.env['siantou.ems.core.specialty'].sudo().search([
                    ('field_of_study_id.cycle_id', '=', cycle.id)
                ])
                diplo_requis_ids = http.request.env['oe.school.course.degree'].sudo().search([('cycle_ids', 'in', cycle.id)])

                if specialty_ids and level_ids:
                    data.append({
                        'id': cycle.id,
                        'code': cycle.code,
                        'name': cycle.name,
                        'specialites': [{
                                'id': specialty_id.id, 
                                'code': specialty_id.code, 
                                'name': '{} - {}'.format(specialty_id.code, specialty_id.name),
                                'school_name': specialty_id.field_of_study_id.school_id.name,
                                'field_of_study_name': specialty_id.field_of_study_id.name,
                                'options':[{'id': opt.id, 'code': opt.code, 'name': opt.name} for opt in specialty_id.option_ids]
                            } 
                            for specialty_id in specialty_ids
                        ],
                        'niveaux': [{'id': niv.id, 'name': niv.name} for niv in level_ids],
                        'diplo_requis': [{'id': diplo.id, 'name': diplo.name} for diplo in diplo_requis_ids]
                    })

            # _logger.info(f"=========== data :: {data}") 
            if data:
                return http.Response(
                    json.dumps({
                        'status': 200,
                        "message": "Données récupérées avec succès",
                        'data':data,
                    })
                )
            else:
                return http.Response(
                    json.dumps({
                        'status': 500,
                        "code": "SERVER_ERROR",
                        "message": "Erreur interne du serveur.",
                        'details':"Les cycles et leurs niveaux, et leurs diplômes requis, les spécialités  doivent être bien configurés",
                    })
                )
        else:
            return http.Response(
                json.dumps({
                    'status': 204,
                    "code": "",
                    "message": "Pas de cycle",
                    "details": "Pas de cycle",
                })
            )


    @http.route('/api/v1/specialites/<int:id>/options', type="http", methods=['GET'], cors="*", website=True, auth="public")
    def list_options_of_specialite(self, id):
        datas = []
        specialty_id = http.request.env['siantou.ems.core.specialty'].sudo().search([('id', '=', id)], limit=1)
        if specialty_id:
            options = http.request.env['siantou.ems.core.option'].sudo().search([('specialty_id', '=', specialty_id.id)])
            datas=[{'id':opt.id, 'name': opt.name} for opt in options]
        return http.Response(
            json.dumps(datas)
        )


    @http.route('/api/v1/<int:id>/etudiants', type="http", methods=['GET'], cors="*", website=True, auth="public")
    def get_etudiant_by_id(self, id,**kw):
        try:
            # _logger.info(f"=========== id:: {id}")
            year_id = http.request.env['siantou.ems.core.year'].sudo().search(
                [('is_active', '=', True),],
                limit=1
            )
            etudiant = http.request.env['oe.school.student.enrollment'].sudo().search([
                    ('id','=', id),
                    ('year_id','=', year_id.id)
                ],
                limit=1
            )
            # _logger.info(f'=================Étudiant :: {etudiant}')
            # _logger.info(f'=================Étudiant :: {etudiant}')
            # _logger.info(f'=================year_id :: {year_id.name}')
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
                        'data': f"Erreur lors de la récuperation des informations de l'étudiant : {etudiant.name}"
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


    def create_enroll_document(self, candidat, file):
        # Création des document pour chaque candidature
        document_obj = http.request.env['oe.school.student.enrollment.file']

        if file:
            dmd_id = document_obj.create({
                "student_enrollemnt_id": candidat.id,
            })
            file_dmd = file
            mime_type = file_dmd.content_type
            attachment_id = http.request.env['ir.attachment'].sudo().create({
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


    @http.route('/api/v1/etudiants/<int:id>/upload/docs', type="http", methods=['post'], cors="*", website=True, auth="public", csrf=False)
    def upload_doc_etudiant_by_id(self, id,**kw):
        documents = []
        try:
            year_id = http.request.env['siantou.ems.core.year'].sudo().search(
                [('is_active', '=', True),],
                limit=1
            )
            etudiant = http.request.env['oe.school.student.enrollment'].sudo().search([
                    ('student_id', '=', id),
                    ('year_id','=', year_id.id)
                ], 
                limit=1
            )
            _logger.info(f'Étudiant : {etudiant}')

            files = http.request.httprequest.files.getlist('file')
            _logger.info(files)
            if etudiant:
                if files:
                    for file in files:
                        _logger.info(file.filename)
                        file_name = file.filename
                        attachment_id = http.request.env['ir.attachment'].sudo().create({
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
                return http.Response(
                    json.dumps({
                        'status': 'success',
                        'etudiant_id':etudiant.id,
                    })
                )
            else:
                return http.Response(
                    json.dumps({
                        'status': 'error',
                        'data': f"Erreur lors de la savegarde des documents"
                    })
                )
        except Exception as e:
            return http.Response(
                json.dumps({
                    'status': 'error',
                    'data': f"{e.args}"
                })
            )


    @http.route('/api/v1/save', type="http", methods=['POST'], cors="*", website=True, auth="public", csrf=False)
    def admission_form_submit(self, **kwargs):
        data = json.loads(http.request.httprequest.data)
        # _logger.info(f"=========== data :: {data}")
        is_existing = True

        try:
            data['cycle_id'] = data['specialites'][0]['cycle_id']
            data['specialty_id'] = data['specialites'][0]['specialty_id']
            data['option_id'] = data['specialites'][0]['option_id']
            data['level_id'] = data['specialites'][0]['niveau_id']
            data['type_cour'] = data['specialites'][0]['type_cour']
            data['annee_acad'] = data['specialites'][0]['annee_acad_id']

            if not data['option_id']:
                data['option_id'] = False

            if len(data['specialites']) > 1:
                specialites = data['specialites'][1:]
            else:
                specialites = []

            del(data['specialites'])

            # _logger.info(f"=========== specialites :: {specialites}")

            #=== Get matricule generated
            code_enrol = self.generate_code()
            while is_existing:
                etudiant_enrol = http.request.env['oe.school.student.enrollment'].sudo().search(
                    [('code_enrol', '=', code_enrol)],
                    limit=1
                )
                if not etudiant_enrol:
                    data['code_enrol'] = code_enrol
                    is_existing = False

            year_id = http.request.env['siantou.ems.core.year'].sudo().search(
                [('is_active', '=', True),],
                limit=1
            )
            #=== récupération de la session d'admission active
            session_id = http.request.env['siantou.session'].sudo().search(
                [
                    ('state', '=', 'admission'),
                    ('year_id', '=', year_id.id),
                    ('cycle_ids', 'in', data['cycle_id']),
                ],
                limit=1
            )

            # _logger.info(session_id)
            # _logger.info(session_id.cycle_ids)
            # on Vérifie si le cycle choisi par l'étudion est dans la session d'admission active
            is_present = session_id.cycle_ids.filtered(lambda cycle: cycle.id == data['cycle_id'])
            if session_id and bool(is_present):
                # _logger.info(is_present)
                # _logger.info(session_id.cycle_ids)
                #=== récupération du régistre de la session d'admission active et correspondant au cycle choisi par l'utilisateur
                registre_id = http.request.env['siantou.session.registre'].sudo().search(
                    [
                        ('session_id', '=', session_id.id),
                        ('cycle_id', '=', data['cycle_id'])
                    ],
                    limit=1
                )
                _logger.info(registre_id)
                if registre_id:
                    #=== Insertion de l'utilisateur dans le registre correspondant à son cycle
                    data['registre_id'] = registre_id.id
                    # documents = []
                    # _logger.info("======== etudiant pas encore crée")

                    if not data['nationalite']:
                        data['is_autre_pays'] = True
                    else:
                        data['is_autre_pays'] = False

                    etudiant = http.request.env['oe.school.student'].sudo().search([
                        ('last_name', '=', data['last_name']),
                        ('first_name', '=', data['first_name']),
                        ('specialty_id', '=', data['specialty_id']),
                        ('option_id', '=', data['option_id']),
                        ('level_id', '=', data['level_id']),
                        ('type_cour', '=', data['type_cour']),
                        ('year_id', '=', year_id.id),

                    ], limit=1)
                    if not etudiant:
                        etudiant = http.request.env['oe.school.student'].sudo().create(data)
                        if etudiant:
                            for specialite in specialites:
                                if not specialite['option_id']:
                                    specialite['option_id'] = False
                                etudiant.student_enroll_ids.create({
                                    'code_enrol': etudiant.code_enrol,
                                    'year_id': year_id.id,
                                    'school_id': etudiant.school_id.id,
                                    'cycle_id': specialite['cycle_id'],
                                    'specialty_id': specialite['specialty_id'],
                                    'option_id': specialite['option_id'],
                                    'type_cour': specialite['type_cour'],
                                    'status_univ': etudiant.status_univ,
                                    'status_acad': 'no_red',
                                    'session_lieu_obt': etudiant.session_lieu_obt,
                                    'dern_etab_freq': etudiant.dern_etab_freq,
                                    'level_id': specialite['niveau_id'],
                                    'diplo_requis_ids': etudiant.diplo_requis_ids.ids,
                                    'student_id': etudiant.id,
                                    'priority': '2',
                                })
                            return http.Response(
                                json.dumps({
                                    'status': 'success',
                                    'etudiant_id':etudiant.id,
                                })
                            )
                    else:
                        return http.Response(
                            json.dumps({
                                'status': 'error',
                                'data':f"L'étudiant {etudiant.name} existe déjà pour l'année académique {year_id.name}",
                            })
                        )
                else:
                    return http.Response(
                            json.dumps({
                                'status': 'error',
                                'data':"Aucune session d'admission ouverte pour le cycle choisi",
                            })
                        )
            else:
                return http.Response(
                        json.dumps({
                            'status': 'error',
                            'data':"Aucune session d'admission ouverte pour le cycle choisi",
                        })
                    )
        except Exception as e:
            return http.Response(
                json.dumps({
                    'status': 'error',
                    'data':f"{e.args}"
                })
            )


    @http.route('/api/v1/student-old/checking', type="http", methods=['POST'], cors="*", website=True, auth="public", csrf=False)
    def check_old_student(self, **kwargs):
        data = json.loads(http.request.httprequest.data)
        # _logger.info(f"=========== matricule :: {data['matricule']}")
        etudiant = http.request.env['oe.school.student'].sudo().search(
            [
                ('matricule', '=', data['matricule']),
            ],
            limit=1
        )
        
        # _logger.info(f"=========== etudiant :: {etudiant}")
        if etudiant:
            return http.Response(
                json.dumps({
                    'status': 200,
                    'data':{
                        'id':etudiant.id,
                        'last_name':etudiant.last_name,
                        'first_name':etudiant.first_name,
                        'date_naissance':f"{etudiant.date_naissance}",
                        'lieu_naissance':etudiant.lieu_naissance if etudiant.lieu_naissance else '',
                        'sexe':etudiant.sexe,
                        'situat_matri':etudiant.situat_matri,

                        'matricule':etudiant.matricule,
                        'cycle_id':etudiant.cycle_id.id,
                        'specialty_id':etudiant.specialty_id.id,
                        'option_id':etudiant.option_id.id if etudiant.option_id else '',
                        'type_cour':etudiant.type_cour,
                        'niveau':etudiant.level_id.id,
                        'anne_acad_id':etudiant.year_id.id,
                    },
                })
            )
        else:
            return http.Response(
                json.dumps({
                    'status': 500,
                    'data':f"Aucune informations trouvés pour ce matricule : {data['matricule']} ",
                })
            )


    @http.route('/api/v1/student-old/save', type="http", methods=['POST'], cors="*", website=True, auth="public", csrf=False)
    def admission_form_submit_old_student(self, **kwargs):
        data = json.loads(http.request.httprequest.data)
        # _logger.info(f"=========== data :: {data}")
        is_existing = True

        try:
            data['cycle_id'] = data['specialites'][0]['cycle_id']
            data['specialty_id'] = data['specialites'][0]['specialty_id']
            data['option_id'] = data['specialites'][0]['option_id']
            data['level_id'] = data['specialites'][0]['niveau_id']
            data['type_cour'] = data['specialites'][0]['type_cour']
            data['annee_acad'] = data['specialites'][0]['annee_acad_id']

            if not data['option_id']:
                data['option_id'] = False

            if len(data['specialites']) > 1:
                specialites = data['specialites'][1:]
            else:
                specialites = []

            del(data['specialites'])

            # _logger.info(f"=========== specialites :: {specialites}")

            #=== Get matricule generated
            code_enrol = self.generate_code()
            while is_existing:
                etudiant_enrol = http.request.env['oe.school.student.enrollment'].sudo().search(
                    [('code_enrol', '=', code_enrol)],
                    limit=1
                )
                if not etudiant_enrol:
                    data['code_enrol'] = code_enrol
                    is_existing = False

            year_id = http.request.env['siantou.ems.core.year'].sudo().search(
                [('is_active', '=', True),],
                limit=1
            )
            #=== récupération de la session d'admission active
            session_id = http.request.env['siantou.session'].sudo().search(
                [
                    ('state', '=', 'admission'),
                    ('year_id', '=', year_id.id),
                    ('cycle_ids', 'in', data['cycle_id']),
                ],
                limit=1
            )
            is_present = session_id.cycle_ids.filtered(lambda cycle: cycle.id == data['cycle_id'])
            if session_id and bool(is_present):
                registre_id = http.request.env['siantou.session.registre'].sudo().search(
                    [
                        ('session_id', '=', session_id.id),
                        ('cycle_id', '=', data['cycle_id'])
                    ],
                    limit=1
                )
                _logger.info(registre_id)
                if registre_id:
                    #=== Insertion de l'utilisateur dans le registre correspondant à son cycle
                    data['registre_id'] = registre_id.id
                    if data['id']:
                        etudiant_id = http.request.env['oe.school.student'].sudo().search(
                            [
                                ('id', '=', data['id']),
                                ('matricule', '=', data['matricule']),
                            ],
                            limit=1
                        )
                        if etudiant_id:
                            etudiant_enrollment = http.request.env['oe.school.student.enrollment'].sudo().search(
                                [
                                    ('student_id', '=', etudiant_id.id),
                                    ('year_id', '=', year_id.id),
                                    # ('is_active_candidature', '=', True),
                                ],
                                limit=1
                            )

                            if not etudiant_enrollment:
                                #===add field
                                data['student_id'] = etudiant_id.id
                                data['year_id'] = year_id.id
                                data['status_univ'] = 'old'
                                data['type_candidature'] = 'inscript'
                                # school_id = None
                                # specialty_id = http.request.env['siantou.ems.core.specialty'].browse(data['specialty_id'])
                                # if specialty_id:
                                #     data['school_id'] = specialty_id.field_of_study_id.school_id.id
                                #     data['field_of_study_id'] = specialty_id.field_of_study_id.id
                                # class_id =  http.request.env['siantou.ems.core.class'].search([
                                #     ('school_id', '=', data['school_id']),
                                #     ('specialty_id', '=', data['specialty_id']),
                                #     ('option_id', '=', data['option_id']),
                                #     ('level_id', '=', data['level_id']),
                                #     ('year_id', '=', data['year_id']),
                                #     ('type_cour', '=', data['type_cour']),
                                # ], limit=1)
                                # if class_id:
                                #     data['class_id'] = class_id.id
                                # else:

                                data['class_id'] = False

                                etudiant_enrollment = http.request.env['oe.school.student.enrollment'].sudo().create(data)
                                if etudiant_enrollment:
                                    for specialite in specialites:
                                        if not specialite['option_id']:
                                            specialite['option_id'] = False
                                        etudiant_id.student_enroll_ids.create({
                                            'code_enrol': etudiant_id.code_enrol,
                                            'year_id': year_id.id,
                                            'school_id': etudiant_id.school_id.id,
                                            'cycle_id': specialite['cycle_id'],
                                            'specialty_id': specialite['specialty_id'],
                                            'option_id': specialite['option_id'],
                                            'type_cour': specialite['type_cour'],
                                            'status_univ': etudiant_id.status_univ,
                                            'session_lieu_obt': etudiant_id.session_lieu_obt,
                                            'dern_etab_freq': etudiant_id.dern_etab_freq,
                                            'level_id': specialite['niveau_id'],
                                            'diplo_requis_ids': etudiant_id.diplo_requis_ids.ids,
                                            'student_id': etudiant_id.id,
                                            'priority': '2',
                                        })
                                    return http.Response(
                                        json.dumps({
                                            'status': 'success',
                                            'etudiant_id':etudiant_enrollment.id,
                                        })
                                    )
                            else:
                                return http.Response(
                                    json.dumps({
                                        'status': 'error',
                                        'data':f"Votre candidature existe déjà pour l'année {etudiant_enrollment.year_id.name}",
                                    })
                                )
                    else:
                        etudiant_old = http.request.env['oe.school.student.enrollment.old'].sudo().search(
                            [
                                ('matricule', '=', data['matricule']),
                                # ('last_name', '=', data['last_name']),
                                # ('first_name', '=', data['first_name']),
                                ('specialty_id', '=', data['specialty_id']),
                                ('level_id', '=', data['level_id']),
                                ('type_cour', '=', data['type_cour']),
                                ('anne_acad_id', '=', data['annee_acad']),
                                ('year_id', '=', year_id.id),
                            ],
                            limit=1
                        )
                        if not etudiant_old:
                            data['status_univ'] = 'old'
                            data['anne_acad_id'] = data['annee_acad']
                            del(data['annee_acad'])
                            etudiant = http.request.env['oe.school.student.enrollment.old'].sudo().create(data)
                            if etudiant:
                                return http.Response(
                                    json.dumps({
                                        'status': 'success',
                                        'etudiant_id':etudiant.id,
                                    })
                                )
                        else:
                            return http.Response(
                                json.dumps({
                                    'status': 'error',
                                    'data':f"Une demande d'inscription avec ce matricule : {data['matricule']} existe déjà ",
                                })
                            )
                    
                else:
                    return http.Response(
                            json.dumps({
                                'status': 'error',
                                'data':"Aucune session d'admission ouverte",
                            })
                        )
            else:
                return http.Response(
                        json.dumps({
                            'status': 'error',
                            'data':"Aucune session d'admission ouverte",
                        })
                    )
        except Exception as e:
            return http.Response(
                json.dumps({
                    'status': 'error',
                    'data':f"{e.args}"
                })
            )




#========================================================================================================================================
#========================================================================================================================================
#=============================================================CONCOURS===================================================================
#========================================================================================================================================
#========================================================================================================================================

    @http.route('/api/v1/concours/cycles', type="http", methods=['GET'], cors="*", website=True, auth="public")
    def list_competition_courses(self, **kw):
        data = []
        cycles = []
        year_id = http.request.env['siantou.ems.core.year'].sudo().search(
            [('is_active', '=', True),],
            limit=1
        )

        #=== récupération de la session d'admission active de l'année active
        session_ids = http.request.env['siantou.session.competition'].sudo().search(
            [
                ('is_active', '=', True),
                ('year_id', '=', year_id.id),
                ('state', '=', 'admission'),
            ]
        )

        # _logger.info(session_ids)
        if session_ids:
            for session_id in session_ids:
                cycles.append(session_id.cycle_id)

        # _logger.info(f"=========== API cycles :: {cycles}")   
        if cycles:
            for cycle in cycles:
                level_ids = cycle.level_ids
                specialty_ids = http.request.env['siantou.ems.core.specialty'].sudo().search([('field_of_study_id.cycle_id', '=', cycle.id)])
                if specialty_ids and level_ids:
                    data.append({
                        'id': cycle.id,
                        'code': cycle.code,
                        'name': cycle.name,
                        'specialites': [{
                                'id': specialty_id.id, 
                                'code': specialty_id.code, 
                                'name': '{} - {}'.format(specialty_id.code, specialty_id.name),
                                'school_name': specialty_id.field_of_study_id.school_id.name,
                                'field_of_study_name': specialty_id.field_of_study_id.name,
                                'options':[{'id': opt.id, 'name': opt.name} for opt in specialty_id.option_ids]
                            } 
                            for specialty_id in specialty_ids
                        ],
                        'niveaux': [{'id': niv.id, 'name': niv.name} for niv in level_ids],
                    })

            # _logger.info(f"===========>>> data :: {data}")
            if data:
                return http.Response(
                    json.dumps({
                        'status': 200,
                        "message": "Données récupérées avec succès",
                        'data':data,
                    })
                )
            else:
                return http.Response(
                    json.dumps({
                        'status': 500,
                        "code": "SERVER_ERROR",
                        "message": "Erreur interne du serveur.",
                        'details':"Les cycles et leurs niveaux, et leurs diplômes requis, les spécialités  doivent être bien configurés",
                    })
                )
        else:
            return http.Response(
                json.dumps({
                    'status': 204,
                    "code": "",
                    "message": "Pas de cycle",
                    "details": "Pas de cycle",
                })
            )


    @http.route('/api/v1/concours/save', type="http", methods=['POST'], cors="*", website=True, auth="public", csrf=False)
    def admission_competition_submit(self, **kwargs):
        data = json.loads(http.request.httprequest.data)
        # _logger.info(f"=========== data :: {data}")

        try:
            year_id = http.request.env['siantou.ems.core.year'].sudo().search(
                [('is_active', '=', True),],
                limit=1
            )
            #=== récupération de la session d'admission active
            session_competition_id = http.request.env['siantou.session.competition'].sudo().search(
                [
                    ('state', '=', 'admission'),
                    ('year_id', '=', year_id.id),
                    ('cycle_id', '=', data['cycle_id']),
                ],
                limit=1
            )

            # _logger.info(session_competition_id)
            # _logger.info(session_competition_id.cycle_ids)
            # on Vérifie si le cycle choisi par l'étudion est dans la session d'admission active
            # is_present = session_competition_id.cycle_ids.filtered(lambda cycle: cycle.id == data['cycle_id'])

            if session_competition_id:
                # _logger.info(is_present)
                # _logger.info(session_competition_id.cycle_ids)
                #=== récupération du régistre de la session d'admission active et correspondant au cycle choisi par l'utilisateur
                registre_id = http.request.env['siantou.session.registre.competition'].sudo().search(
                    [
                        ('session_competition_id', '=', session_competition_id.id),
                        ('cycle_id', '=', data['cycle_id'])
                    ],
                    limit=1
                )
                _logger.info(registre_id)
                if registre_id:
                    #=== Insertion de l'utilisateur dans le registre correspondant à son cycle
                    data['registre_id'] = registre_id.id
                    # documents = []
                    # _logger.info("======== etudiant pas encore crée")

                    #===== create res partner instance =================
                    partner = None
                    name = '{} {}'.format(data['last_name'], data['first_name'])
                    check_partner = http.request.env['res.partner'].sudo().search([
                            ("name","=",name)
                        ], 
                        limit=1
                    )
                    if not check_partner:
                        partner = http.request.env['res.partner'].sudo().create({
                            "name":name
                        })
                    else:
                        partner = check_partner
                    data['partner_id'] = partner.id
                    
                    # _logger.info(f"=============  data :: {data}")
                    etudiant = http.request.env['oe.school.student.enrollment.competition'].sudo().search([
                        ('last_name', '=', data['last_name']),
                        ('first_name', '=', data['first_name']),
                        ('specialty_id', '=', data['specialty_id']),
                        ('option_id', '=', data['option_id']),
                        ('cycle_acad', '=', data['cycle_acad']),
                        ('year_id', '=', year_id.id),

                    ], limit=1)
                    if not etudiant:
                        etudiant = http.request.env['oe.school.student.enrollment.competition'].sudo().create(data)
                        if etudiant:
                            return http.Response(
                                json.dumps({
                                    'status': 'success',
                                    'etudiant_id':etudiant.id,
                                })
                            )
                    else:
                        return http.Response(
                            json.dumps({
                                'status': 'error',
                                'data':f"Dossier de {etudiant.name} pour l'année {year_id.name} existe déjà",
                            })
                        )
                else:
                    return http.Response(
                            json.dumps({
                                'status': 'error',
                                'data':f"Aucune session d'admission councours ouverte pour le cycle {registre_id.cycle_id.name}",
                            })
                        )
            else:
                return http.Response(
                        json.dumps({
                            'status': 'error',
                            'data':f"Aucune session d'admission ouverte pour le cycle  {session_competition_id.cycle_id.name}",
                        })
                    )
        except Exception as e:
            return http.Response(
                json.dumps({
                    'status': 'error',
                    'data':f"{e.args}"
                })
            )


#========================================================================================================================================
#========================================================================================================================================
#=============================================================CHANGEMENT DES INFORMATIONS ACADEMIQUES====================================
#========================================================================================================================================
#========================================================================================================================================
    @http.route('/api/v1/field-study/change', type="http", methods=['POST'], cors="*", website=True, auth="public", csrf=False)
    def field_study_change_submit(self, **kwargs):
        data = json.loads(http.request.httprequest.data)
        # _logger.info(f"=========== data :: {data}")

        try:
            year_id = http.request.env['siantou.ems.core.year'].sudo().search(
                [('is_active', '=', True),],
                limit=1
            )
 
            etudiant = http.request.env['oe.school.student'].sudo().search([
                ('id', '=', data['id']),
                ('matricule', '=', data['matricule']),
                ('year_id', '=', year_id.id),

            ], limit=1)
            if etudiant:
                student_change_specialty = http.request.env['oe.stud.change.specialty'].sudo().create({
                    'year_id': year_id.id,
                    'school_old_id': etudiant.school_id.id,
                    'cycle_old_id': etudiant.cycle_id.id,
                    'specialty_old_id': etudiant.specialty_id.id,
                    'option_old_id': etudiant.option_id.id,
                    'type_old_cour': etudiant.type_cour,
                    'level_old_id': etudiant.level_id.id,
                    'cycle_new_id': data['cycle_id'],
                    'specialty_new_id': data['specialty_id'],
                    'option_new_id': data['option_id'],
                    'type_new_cour': data['type_cour'],
                    'level_new_id': data['level_id'],
                    'student_id': etudiant.id,
                })
                # etudiant.student_change_specialty_ids.create({
                #     'year_id': year_id.id,
                #     'school_old_id': etudiant.school_id.id,
                #     'cycle_old_id': etudiant.cycle_id.id,
                #     'specialty_old_id': etudiant.specialty_id.id,
                #     'option_old_id': etudiant.option_id.id,
                #     'type_old_cour': etudiant.type_cour,
                #     'level_old_id': etudiant.level_id.id,
                #     'cycle_new_id': data['cycle_id'],
                #     'specialty_new_id': data['specialty_id'],
                #     'option_new_id': data['option_id'],
                #     'type_new_cour': data['type_cour'],
                #     'level_new_id': data['level_id'],
                #     'student_id': etudiant.id,
                # })

                return http.Response(
                    json.dumps({
                        'status': 'success',
                        'etudiant_id':etudiant.id,
                    })
                )
            else:
                return http.Response(
                    json.dumps({
                        'status': 'error',
                        'data':f"L'étudiant {etudiant.name} n'existe pas pour l'année académique {year_id.name}",
                    })
                )
        except Exception as e:
            return http.Response(
                json.dumps({
                    'status': 'error',
                    'data':f"{e.args}"
                })
            )

    @http.route(['/api/modify/subject', '/api/modify/subject/<int:class_id>/<int:old_subject_id>/<int:new_subject_id>'], type='http', auth='public')
    def api_modify_subject(self, class_id=0, old_subject_id=0, new_subject_id=0, **kw):
        classe = http.request.env['siantou.ems.core.class'].sudo().search([('id', '=', class_id)], limit=1)
        if not classe:
            body = {
                'code': 404,
                'message': f'Not found class : {class_id}',
                'data': {}
            }
            data = json.dumps(body)
            headers = {'Content-Type': 'application/json'}
            return http.request.make_response(data, headers=headers, status=404)
        old_subject = http.request.env['siantou.ems.core.subject'].sudo().search([('id', '=', old_subject_id)], limit=1)
        if not old_subject:
            body = {
                'code': 404,
                'message': f'Not found old subject : {old_subject_id}',
                'data': {}
            }
            data = json.dumps(body)
            headers = {'Content-Type': 'application/json'}
            return http.request.make_response(data, headers=headers, status=404)
        new_subject = http.request.env['siantou.ems.core.subject'].sudo().search([('id', '=', new_subject_id)], limit=1)
        if not new_subject:
            body = {
                'code': 404,
                'message': f'Not found new subject : {new_subject_id}',
                'data': {}
            }
            data = json.dumps(body)
            headers = {'Content-Type': 'application/json'}
            return http.request.make_response(data, headers=headers, status=404)
        timetables = http.request.env['siantou.ems.timetable.timetable'].sudo().search([
            ('class_id', '=', classe.id),
            ('subject_id', '=', old_subject.id),
        ])
        timetables = list(timetables)
        for timetable in timetables:
            timetable.write({
                'subject_id': new_subject.id,
                'skip_validation': True,
            })
        body = {
            'code': 200,
            'message': '',
            'data': {
                'class': classe.name,
                'old_subject': old_subject.name,
                'new_subject': new_subject.name,
                'timetables': len(timetables),
            }
        }
        data = json.dumps(body)
        headers = {'Content-Type': 'application/json'}
        return http.request.make_response(data, headers=headers, status=200)

    @http.route(['/api/modify/class', '/api/modify/class/<int:old_class_id>/<int:new_class_id>'], type='http', auth='public')
    def api_modify_class(self, old_class_id=0, new_class_id=0, **kw):
        old_class = http.request.env['siantou.ems.core.class'].sudo().search([('id', '=', old_class_id)], limit=1)
        if not old_class:
            body = {
                'code': 404,
                'message': f'Not found old class : {old_class_id}',
                'data': {}
            }
            data = json.dumps(body)
            headers = {'Content-Type': 'application/json'}
            return http.request.make_response(data, headers=headers, status=404)
        new_class = http.request.env['siantou.ems.core.class'].sudo().search([('id', '=', new_class_id)], limit=1)
        if not new_class:
            body = {
                'code': 404,
                'message': f'Not found new class : {new_class_id}',
                'data': {}
            }
            data = json.dumps(body)
            headers = {'Content-Type': 'application/json'}
            return http.request.make_response(data, headers=headers, status=404)
        timetables = http.request.env['siantou.ems.timetable.timetable'].sudo().search([
            ('class_id', '=', old_class.id),
        ])
        timetables = list(timetables)
        for timetable in timetables:
            timetable.write({
                'school_id': new_class.school_id.id,
                'level_id': new_class.level_id.id,
                'specialty_id': new_class.specialty_id.id,
                'option_id': new_class.option_id.id,
                'class_id': new_class.id,
                'skip_validation': True,
            })
        body = {
            'code': 200,
            'message': '',
            'data': {
                'old_class': old_class.name,
                'new_class': new_class.name,
                'timetables': len(timetables),
            }
        }
        data = json.dumps(body)
        headers = {'Content-Type': 'application/json'}
        return http.request.make_response(data, headers=headers, status=200)

    @http.route(['/api/modify/group', '/api/modify/group/<int:group_id>'], type='http', auth='public')
    def api_modify_group(self, group_id=0, **kw):
        group = http.request.env['siantou.ems.timetable.group'].sudo().search([('id', '=', group_id)], limit=1)
        if not group:
            body = {
                'code': 404,
                'message': f'Not found group : {group_id}',
                'data': {}
            }
            data = json.dumps(body)
            headers = {'Content-Type': 'application/json'}
            return http.request.make_response(data, headers=headers, status=404)
        timetables = http.request.env['siantou.ems.timetable.timetable'].sudo().search([
            ('group_id', '=', group.id),
        ])
        timetables = list(timetables)
        for timetable in timetables:
            timetable.write({
                'school_id': timetable.class_id.school_id.id,
                'level_id': timetable.class_id.level_id.id,
                'specialty_id': timetable.class_id.specialty_id.id,
                'option_id': timetable.class_id.option_id.id,
                'class_id': timetable.class_id.id,
                'skip_validation': True,
            })
        body = {
            'code': 200,
            'message': '',
            'data': {
                'group': group.name,
                'timetables': len(timetables),
            }
        }
        data = json.dumps(body)
        headers = {'Content-Type': 'application/json'}
        return http.request.make_response(data, headers=headers, status=200)
