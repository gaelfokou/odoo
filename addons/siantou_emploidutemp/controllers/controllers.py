# -*- coding: utf-8 -*-
from odoo import http
import logging

_logger = logging.getLogger(__name__)

class siantou_emploidutemp_emploidutemp_controller(http.Controller):
    # @http.route('/siantou_emploidutemp/emploidutemp', auth='public', type='http')
    # def index(self, **kw):
    #     return "Hello, world"

    @http.route('/siantou_emploidutemp/emploidutemp', auth='public', type='http')
    def list(self, **kw):
        return http.request.render('siantou_emploidutemp.emploidutemp_listing', {
            'root': '/siantou_emploidutemp/emploidutemp',
            'emploidutemps': http.request.env['siantou_emploidutemp.emploidutemp'].search([]),
        })

    @http.route('/siantou_emploidutemp/emploidutemp/<model("siantou_emploidutemp.emploidutemp"):obj>', auth='public', type='http')
    def object(self, obj, **kw):
        return http.request.render('siantou_emploidutemp.emploidutemp_object', {
            'emploidutemp': obj
        })

class siantou_emploidutemp_semestre_controller(http.Controller):
    @http.route('/siantou_emploidutemp/semestre/<int:id>', auth='public', type='http', method=['GET'])
    def generate(self, id, **kw):
        _logger.info(f'----------- tototototototo Your information log message {id} -----------')
        return http.request.render('siantou_emploidutemp.semestre_listing', {
            'root': '/siantou_emploidutemp/semestre',
            'semestres': http.request.env['siantou_emploidutemp.semestre'].search([
                ('id', '=', id),
            ])
        })
