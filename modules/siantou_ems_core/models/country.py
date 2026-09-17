from odoo import models, fields, api, tools, _


class Country(models.Model):
    _name = 'siantou.ems.core.country'
    _description = 'Pays'

    code = fields.Char(
        string='Code',
        required=True,
    )

    name = fields.Char(
        string='Nom',
        required=True,
    )

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code du pays doit être unique.'),
    ]


class Region(models.Model):
    _name = 'siantou.ems.core.region'
    _description = 'Région'

    code = fields.Char(
        string='Code',
        compute='_compute_code',
        store=True,
    )

    @api.depends('name')
    def _compute_code(self):
        for record in self:
            name = record.name
            while True:
                if name.find('-') != -1:
                    name = name.replace('-', ' ')
                elif name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            code = []
            for i, x in enumerate(name.split(' ')):
                if i == 0:
                    code.append(x[:5])
                else:
                    code.append(x[:3])
            code = ''.join(code)
            code = code.upper()
            record.code = code

    @api.onchange('name')
    def _onchange_code(self):
        for record in self:
            record._compute_code()

    name = fields.Char(
        string='Nom',
        required=True,
    )

    country_id = fields.Many2one(
        'siantou.ems.core.country',
        string='Pays',
        required=True,
    )

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code de la région doit être unique.'),
    ]


class City(models.Model):
    _name = 'siantou.ems.core.city'
    _description = 'Ville'

    code = fields.Char(
        string='Code',
        compute='_compute_code',
        store=True,
    )

    @api.depends('name')
    def _compute_code(self):
        for record in self:
            name = record.name
            while True:
                if name.find('-') != -1:
                    name = name.replace('-', ' ')
                elif name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            code = []
            for i, x in enumerate(name.split(' ')):
                if i == 0:
                    code.append(x[:5])
                else:
                    code.append(x[:3])
            code = ''.join(code)
            code = code.upper()
            record.code = code

    @api.onchange('name')
    def _onchange_code(self):
        for record in self:
            record._compute_code()

    name = fields.Char(
        string='Nom',
        required=True,
    )

    region_id = fields.Many2one(
        'siantou.ems.core.region',
        string='Région',
        required=True,
    )

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code de la ville doit être unique.'),
    ]


class Quarter(models.Model):
    _name = 'siantou.ems.core.quarter'
    _description = 'Quartier'

    code = fields.Char(
        string='Code',
        compute='_compute_code',
        store=True,
    )

    @api.depends('name')
    def _compute_code(self):
        for record in self:
            name = record.name
            while True:
                if name.find('-') != -1:
                    name = name.replace('-', ' ')
                elif name.find('  ') != -1:
                    name = name.replace('  ', ' ')
                else:
                    break
            name = name.strip()
            code = []
            for i, x in enumerate(name.split(' ')):
                if i == 0:
                    code.append(x[:5])
                else:
                    code.append(x[:3])
            code = ''.join(code)
            code = code.upper()
            record.code = code

    @api.onchange('name')
    def _onchange_code(self):
        for record in self:
            record._compute_code()

    name = fields.Char(
        string='Nom',
        required=True,
    )

    city_id = fields.Many2one(
        'siantou.ems.core.city',
        string='Ville',
        required=True,
    )

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code du quartier doit être unique.'),
    ]
