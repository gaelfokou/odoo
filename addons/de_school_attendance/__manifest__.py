# -*- coding: utf-8 -*-
{
    'name': "Student Attendance",

    'summary': """
        Efficiently track and manage student attendance with our user-friendly attendance module.""",

    'description': """
        Efficiently track and manage student attendance with our user-friendly attendance module.
    """,
    'author': "Dynexcel",
    'website': "https://www.dynexcel.com",
    'category': 'School/Industries',
    'version': '17.0.0.1',
    'depends': [
        'de_school'
    ],
    'data': [
        'security/attendance_security.xml',
        'security/ir.model.access.csv',
        'views/attendance_menu.xml',
        'views/res_config_settings_views.xml',
        'views/attendance_views.xml',
        'views/attendance_register_views.xml',
        'views/attendance_sheet_views.xml',
        #'views/student_attendance_views.xml',
        #'reports/report_student_attendance_views.xml',
        'wizards/mark_attendance_wizard_views.xml',
        'wizards/report_attendance_xlsx_wizard_views.xml',
        'wizards/save_xlsx_views.xml',
    ],
    'license': 'LGPL-3',
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
