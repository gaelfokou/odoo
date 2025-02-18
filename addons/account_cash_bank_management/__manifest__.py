# -*- coding: utf-8 -*-
{
    'name': "Account Cash Bank Management",

    'summary': "The objective of this module is to manage cash and banking flows.",

    'description': """
    
    """,

    'author': "No name",
    'website': "",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account_accountant', 'account_payment', 'siantou_ems_core'],

    # always loaded
    'data': [
        # Wizards
        'wizards/encaissement_frais_etudiant_views.xml',

        'views/account_move_views.xml',
        'views/account_bank_statement_views.xml',
        'views/account_move_line_views.xml',

        # Rapports
        'report/paper_format_templates.xml',
        'report/layout.xml',
        'report/recu_paiement.xml',
        'report/report_recu_paiement_pdf_template.xml',
        'report/action.xml',
    ],
    # only loaded in demonstration mode
    'demo': [],
}
