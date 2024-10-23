# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Genre(models.Model):
    _name = 'oe.library.genre'
    _description = 'Book Genre'

    name = fields.Char(string='Name', required=True)