# -*- coding: utf-8 -*-
from odoo import http
import logging

_logger = logging.getLogger(__name__)

class siantou_emploidetemp(http.Controller):
    # @http.route('/siantou_emploidetemp/emploidetemp', auth='public', type='http')
    # def index(self, **kw):
    #     return "Hello, world"

    @http.route('/siantou_emploidetemp/emploidetemp', auth='public', type='http')
    def list(self, **kw):
        return http.request.render('siantou_emploidetemp.emploidetemp_listing', {
            'root': '/siantou_emploidetemp/emploidetemp',
            'emploidetemps': http.request.env['siantou_emploidetemp.emploidetemp'].search([]),
        })

    @http.route('/siantou_emploidetemp/emploidetemp/<model("siantou_emploidetemp.emploidetemp"):obj>', auth='public', type='http')
    def object(self, obj, **kw):
        return http.request.render('siantou_emploidetemp.emploidetemp_object', {
            'emploidetemp': obj
        })

    @http.route('/siantou_emploidetemp/semestre/<int:id>', auth='public', type='http', method=['GET'])
    def generate(self, **kw):
        try:
            _logger.info(f'----------- tototototototo Your information log message {id} -----------')
            _logger.warning(f'----------- tototototototo Your warning log message {id} -----------')
            _logger.error(f'----------- tototototototo Your error log message {id} -----------')
        except Exception as e:
            _logger.exception(f'----------- tototototototo An error occurred : {e} -----------')
        semestres = []
        semestres.append(id)
        return http.request.render('siantou_emploidetemp.semestre_listing', {
            'semestres': semestres
        })
