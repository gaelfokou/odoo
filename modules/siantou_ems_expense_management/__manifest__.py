# -*- coding: utf-8 -*-
{
    'name': "Siantou Gestion des Dépenses",

    'summary': "Module de gestion des dépenses",

    'description': """
        Création des dépenses
        Workflow d'approbation d'une dépense
        Comptabilisation d'une dépense en passant par la caisse
        Comptabilisation d'un dépense en passant par la banque
    """,

    'author': "ICCSOFT, Dongmo dylan",
    'website': "",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Expense',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'hr_expense',
        'siantou_ems_core',
    ],

    # always loaded
    'data': [
        'views/actions.xml',
        'views/menus.xml',
        'views/hr_expense_views.xml',
        'views/hr_expense_sheet_views.xml',
    ],
}

