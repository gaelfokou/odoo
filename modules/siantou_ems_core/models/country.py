from odoo import models, fields

class Country(models.Model):
    _name = 'siantou.ems.core.country'
    _description = 'Gestion des pays'

    # code du pays
    code = fields.Char(
        'Code',
        required=True,
    )
    # Nom du pays
    name = fields.Char(
        'Nom',
        required=True,
    )

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Le code du pays doit être unique.'),
        ('unique_name', 'unique(name)', 'Le nom du pays doit être unique.'),
    ]

class Region(models.Model):
    _name = 'siantou.ems.core.region'
    _description = 'Gestion des régions'

    # Nom de la région
    name = fields.Char(
        'Nom',
        required=True,
    )
    country_id = fields.Many2one(
        'siantou.ems.core.country',
        string='Pays',
        required=True,
    )
    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Le nom de la région doit être unique.'),
    ]

class City(models.Model):
    _name = 'siantou.ems.core.city'
    _description = 'Gestion des villes'

    # Nom de la ville
    name = fields.Char(
        'Nom',
        required=True,
    )
    region_id = fields.Many2one(
        'siantou.ems.core.region',
        string='Région',
        required=True,
    )
    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Le nom de la ville doit être unique.'),
    ]

class Quarter(models.Model):
    _name = 'siantou.ems.core.quarter'
    _description = 'Gestion des quartiers'

    # Nom du quartsier
    name = fields.Char(
        'Nom',
        required=True,
    )
    city_id = fields.Many2one(
        'siantou.ems.core.city',
        string='Ville',
        required=True,
    )
    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Le nom du quartier doit être unique.'),
    ]

