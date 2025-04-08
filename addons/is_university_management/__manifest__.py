{
    'name': "ICCSOFT - University Core Module",
    'summary': """
        Core Module of University Management System
    """,
    'description': """
        Transform educational administration with the ICCSOFT University Management Core Module.
    """,
    'author': "ICCSOFT S.A.",
    'website': "https://iccsoft.cm/",
    'category': 'Education',
    'version': '17.0.0.3',
    'depends': ['base','hr'],
    'data': [
        'security/ir.model.access.csv',

        'views/academic_year_views.xml',
        'views/availability_views.xml',
        'views/batch_views.xml',
        'views/building_views.xml',
        'views/classroom_views.xml',
        'views/field_of_study_views.xml',
        'views/level_views.xml',
        'views/program_views.xml',
        'views/schedule_views.xml',
        'views/school_views.xml',
        'views/semester.xml',
        'views/student_views.xml',
        'views/subject_views.xml',
        'views/teacher_views.xml',
        'views/timetable_views.xml',
        'views/timetable_wizard_views.xml',

        'views/menu_views.xml',
    ],
    'demo': [
        'demo/level_demo.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
