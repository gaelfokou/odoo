# -*- coding: utf-8 -*-
{
    'name': "SIANTOU - EMS Core App",
    'category': 'Education',
    'version': '17.0.0.0',
    'depends': ['base','hr'],
    'data': [
        # Fichiers de sécurité
        'security/module_category_school_management.xml',
        'security/group_school_management.xml',
        'security/ir.model.access.csv',

        # Fichier des menus
        'views/menu_views.xml',

        # Fichier des vues
        'views/year_views.xml',
        'views/semester_views.xml',
        'views/fieldofstudy_views.xml',
        'views/subject_views.xml',
        'views/teacher_views.xml',
        'views/building_views.xml',
        'views/classroom_views.xml',
        'views/level_views.xml',
        'views/university_views.xml',

        'views/student_enrollment_views.xml',
        'views/course_views.xml',
        'views/degree_course_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
