# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class Iccsoft(http.Controller):
    @http.route('/iccsoft/mangatheque', auth='public')
    def index(self, **post):
        Manga = request.env['iccsoft.manga']
        return request.render('iccsoft.mangatheque', {
            'mangas': Manga.search([])
        },
        **post)

#     @http.route('/iccsoft/iccsoft/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('iccsoft.listing', {
#             'root': '/iccsoft/iccsoft',
#             'objects': http.request.env['iccsoft.iccsoft'].search([]),
#         })

#     @http.route('/iccsoft/iccsoft/objects/<model("iccsoft.iccsoft"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('iccsoft.object', {
#             'object': obj
#         })
