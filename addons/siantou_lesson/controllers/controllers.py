# -*- coding: utf-8 -*-
from odoo import http


class siantou_lesson(http.Controller):
    # @http.route('/siantou/lesson', type='http', auth='public', website=True)
    # def index(self, **kw):
    #     return "Hello, world"

    @http.route('/siantou/lesson', type='http', auth='public', website=True)
    def list(self, **kw):
        return http.request.render('siantou_lesson.listing', {
            'root': '/siantou/lesson',
            'lessons': http.request.env['siantou.lesson'].search([]),
        })

    @http.route('/siantou/lesson/<model("siantou.lesson"):obj>', type='http', auth='public', website=True)
    def object(self, obj, **kw):
        return http.request.render('siantou_lesson.object', {
            'lesson': obj
        })
