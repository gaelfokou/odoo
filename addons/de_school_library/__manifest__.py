# -*- coding: utf-8 -*-
{
    'name': "Openrol - Library",

    'summary': """
    Empowering Education Through Efficient Library Management
        """,

    'description': """
School Managmeent - Library App
================================

Features:
 - User-friendly interface: Intuitive and easy-to-navigate dashboard for students, teachers, and librarians.
 - Catalog management: Efficient organization and management of books, journals, and multimedia resources; advanced search and filter options to locate items quickly.
 - Circulation management: Streamlined check-in and check-out processes; automated due date reminders and overdue notifications.
 - User management: Student, teacher, and staff profiles with personalized access and borrowing limits; role-based access control.
 - Inventory management: Real-time tracking of inventory levels and status updates; tools for adding, updating, and deleting library items.
 - Reservation system: Ability for users to reserve books and resources online; notification system for available reservations.
    """,
    'author': "Dynexcel",
    'website': "https://www.dynexcel.com",
    'category': 'CRM/Sale/Industries',
    'version': '17.0.0.2',
    'depends': [
        'de_school',
        'sale_stock',
        'sale_management',
        'web'
    ],
    'data': [
        'security/library_security.xml',
        'security/ir.model.access.csv',
        'data/library_data.xml',
        'views/library_menu.xml',
        'views/genre_views.xml',
        'views/fee_periods_views.xml',
        'views/product_views.xml',
        'views/res_partner_views.xml',
        'views/publisher_views.xml',
        'views/author_views.xml',
        'views/sale_order_line_views.xml',
        'views/sale_order_views.xml',
        'views/student_views.xml',
        'views/teacher_views.xml',
        'views/agreement_views.xml',
        #'wizards/fee_configurator_views.xml',
        'wizards/order_processing_views.xml',
        'reports/report_library_views.xml',
    ],
    'js': [
        #'de_school_library/static/src/js/library_fee_config_wizard.js',
    ],
    'assets': {
       'web.assets_backend': [
           #'de_school_library/static/src/js/library_fee_config_wizard.js',
           #'de_school_library/static/src/js/library_fee_config_wizard.js',
           #'de_school_library/static/src/**/*',
       ],
    },
    'license': 'LGPL-3',
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
