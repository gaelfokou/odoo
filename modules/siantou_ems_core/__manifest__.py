# -*- coding: utf-8 -*-
{
    'name': "SIANTOU - EMS Core App",
    'category': 'Education',
    'version': '17.0.0.0',
    'depends': ['base', 'web', 'sale', 'board', 'hr','account','mail'],
    'data': [
        # Fichiers de datas
        # 'data/email_template_preinscription.xml',
        # 'data/email_template_preinscription_conditionnelle.xml',
        # 'data/sequence_preinscription.xml',

        # Fichiers de sécurité
        'security/module_category_school_management.xml',
        'security/group_school_management.xml',
        'security/ir.model.access.csv',

        # Fichier des groups
        'views/res_groups_action.xml',
        'views/res_groups_menu.xml',

        # Fichier des menus
        'views/menu_views.xml',

        # Fichier de la section admin
        # 'views/admin_views.xml',

        # Fichier des vues
        'views/year_views.xml',
        'views/portal_views.xml',
        'views/semester_views.xml',
        'views/fieldofstudy_views.xml',
        'views/subject_views.xml',
        'views/progress_report_views.xml',
        'views/subject_session_views.xml',
        'views/teacher_views.xml',
        'views/building_views.xml',
        'views/campus_views.xml',
        'views/classroom_views.xml',
        'views/level_views.xml',
        'views/university_views.xml',
        'views/students_career_views.xml',
        'views/batch_views.xml',
        'views/school_views.xml',
        'views/admission_registre_view.xml',
        'views/admission_session_view.xml',
        'views/syllabus_views.xml',
        'views/unite_enseignement_views.xml',
        'views/specialty_views.xml',
        'views/option_views.xml',
        'views/partenaire_univ_views.xml',
        'views/slot_views.xml',

        'views/student_enrollment_views.xml',
        'views/students_views.xml',
        'views/course_views.xml',
        'views/degree_course_views.xml',
        # 'views/fee_struct_views.xml',
        # 'views/fee_struct_line_views.xml',

        # 'views/fee_enrollment_views.xml',
        'views/country_views.xml',
        'views/region_views.xml',
        'views/city_views.xml',
        'views/quarter_views.xml',
        'views/class_division_views.xml',
        'views/country_views.xml',
        'views/production_pe.xml',
        'views/teacher_avaibility_views.xml',

        #=======Vue hérité pour les créances
        # 'views/account_move.xml',

        #=======Vue hérité pour les modales
        'wizard/fee_student_wizard.xml',
        'wizard/student_enroll_admission_wizard.xml',

        # Fichier de vue timetable
        'views/timetable_views.xml',
        'views/timetable_group_views.xml',
        'views/timetable_wizard_views.xml',
        'views/timetable_print_wizard_views.xml',
        'views/timetable_exception_views.xml',
        'report/timetable_template.xml',
        'report/timetable_percentage_template.xml',
        'report/teacher_template.xml',
        'report/student_template.xml',
        'report/classroom_template.xml',
        'report/class_template.xml',
        'report/subject_template.xml',
        'report/progress_report_template.xml',
        'report/daily_attendance_template.xml',
        'report/report_student_core.xml',

        #=========== Fichier du dashboard
        'views/ems_core_dashboard.xml',

        #=========== Fichier de sequence
        'data/employee_sequence.xml',
        'data/student_sequence.xml',
        'data/exam_score_sequence.xml',
        'data/menu.xml',
        'data/action_server_student.xml',
        'views/student_component_views.xml',
        'views/data_request_wizard_views.xml',
        'views/timetable_filter_wizard_views.xml',
        'views/timetable_group_copier_wizard_views.xml',
        'views/class_ue_copier_wizard_views.xml',
        'views/teacher_filter_wizard_views.xml',
        'views/student_filter_wizard_views.xml',
        'views/classroom_filter_wizard_views.xml',
        'views/class_division_filter_wizard_views.xml',
        'views/subject_filter_wizard_views.xml',
        'views/progress_report_filter_wizard_views.xml',
        'views/daily_attendance_filter_wizard_views.xml',
        'views/hourly_rate_views.xml',
        'views/teacher_hourly_rate_views.xml',
        'views/exam_score_views.xml',
        'views/subject_score_views.xml',
        'views/supervision_views.xml',
        'views/daily_attendance_views.xml',
        'views/hr_department_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'siantou_ems_core/static/src/components/**/*.js',
            'siantou_ems_core/static/src/components/**/*.xml',
            'siantou_ems_core/static/src/components/**/*.scss',
            'siantou_ems_core/static/src/js/student_component.js',
        	'siantou_ems_core/static/src/xml/student_component.xml',
        ],
        'web.assets_frontend': [
            'siantou_ems_core/static/src/css/main.css',
        ],
    },
}
