# -*- coding: utf-8 -*-
{
    'name': "Examens & notes",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "ICCSOFT SA - Landry MVILONGO",
    'website': "http://www.iccsoft.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','siantou_ems_core','siantou_ems_fee', 'mail'],

    # always loaded
    "data": [
        #security
        "security/security.xml",
        "security/ir.model.access.csv",

        "views/menu.xml",
        "views/type_examen_views.xml",
        "views/date_butoire_exam.xml",
        "views/session_examen_rattrapage_views.xml",
        "views/grade_examen_views.xml",
        "views/secretariat_examen_views.xml",
        "views/session_exam_views.xml",
        # "views/exam_views.xml",
        "views/subject_exam_views.xml",
        "views/exam_attendees_views.xml",
        "views/exam_add_code_mark_views.xml",
        "views/exam_add_mark_teacher_views.xml",
        "views/exam_result_subject_views.xml",

        'wizards/attendees_attendance_wizard_views.xml',
        # 'wizards/examen_anonyme_code.xml',
        # 'wizards/generate_marksheets_views.xml',

        #===== REPORTS
        'reports/report_student_examen_mark.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'assets': {
        'web._assets_font': [
            "siantou_ems_examen/static/src/scss/font.scss",
            # 'siantou_ems_examen/static/src/css/font.css',
        ],
    },
}
