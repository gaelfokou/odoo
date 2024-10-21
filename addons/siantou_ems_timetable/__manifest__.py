# -*- coding: utf-8 -*-
{
    'name': "SIANTOU - EMS Timetable App",
    'category': 'Education',
    'version': '17.0.0.0',
    'depends': ['siantou_ems_core'],
    'data': [
        # Fichiers de sécurité
        'security/ir.model.access.csv',

        # Fichier des menus
        'views/menu_views.xml',

        # Fichier des vues
        'views/timetable_views.xml',
        'views/timetable_wizard_views.xml',
        'views/timetable_print_wizard_views.xml',
        'report/timetable_reports.xml',
        'report/timetable_template.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
