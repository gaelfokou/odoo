# -*- coding: utf-8 -*-
{
    'name': "iccsoft",

    'summary': """
        Application de gestion de ICCSOFT""",

    'description': """
        Cette application vous permet de gérer toutes les activités de ICCSOFT
    """,

    'author': "ICCSOFT",
    'website': "https://www.iccsoft.cm",

    'application': True,

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'security/iccsoft_security.xml',
        'security/ir.model.access.csv',
        'wizard/note.xml',
        'views/manga.xml',
        'report/fiche_manga.xml',
        'report/mangatheque.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
