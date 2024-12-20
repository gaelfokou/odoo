# -*- coding: utf-8 -*-
{
    'name': "Gestion des notes & examens",

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
    'depends': ['base','mail'],

    # always loaded
    "data": [
        #data
        "data/sequences.xml",
        "data/type_examen.xml",

        #security
        "security/security.xml",
        "security/ir.model.access.csv",

        #views
        #examen interne
        "views/examen_interne/aft_plannifier.xml",
        "views/examen_interne/aft_exemen_registre.xml",
        "views/examen_interne/aft_exame_add_note.xml",
        "views/examen_interne/aft_type_examen.xml",
        "views/examen_interne/aft_admission_registre.xml",
        "views/examen_interne/aft_admission_student_moyenne.xml",
        "views/examen_interne/aft_examen_student.xml",
        "views/examen_interne/aft_examen_student_line.xml",
        "views/examen_interne/aft_examen_student_subject.xml",
        "views/examen_interne/aft_student.xml",
        "views/examen_interne/aft_rattrapage_registre.xml",
        "views/examen_interne/aft_rattrapage_subject.xml",
        "views/examen_interne/aft_rattrapage_subject_parent.xml",
        "views/examen_interne/aft_rattrapage_ue.xml",
        "views/examen_interne/education_promotion_annee.xml",
        "views/examen_interne/aft_update_note.xml",
        "views/examen_interne/student_qr_code_views.xml",
        "views/examen_interne/examen_actions_valide_server.xml",
        "views/examen_interne/examen_actions_confirm_server.xml",
        "views/examen_interne/aft_examen_student_subject_parent.xml",
        "views/examen_interne/aft_examen_deliberation_student.xml",
        "views/examen_interne/aft_examen_deliberation_jury.xml",
        


        "views/menu.xml",
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'assets': {
        'web._assets_font': [
            "aft_examen/static/src/scss/font.scss",
            # 'aft_examen/static/src/css/font.css',
        ],
    },
}
