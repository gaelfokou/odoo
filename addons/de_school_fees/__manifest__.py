# -*- coding: utf-8 -*-
{
    'name': "Openrol - Fee Managment",

    'summary': """
    All-in-One Fee Solution
        """,

    'description': """
Openrol - Fee Management App
================================
Features:
- **Fee Structure:** Define customizable fee structures tailored to your institution's needs.
- **Fee Particulars:** Organize and track specific fee components with ease and transparency.
- **Schedule Fees:** Plan and automate fee scheduling for timely collections.
- **Late Fees & Fine Management:** Automate calculations and management of late fees and fines.
- **Arrear Management:** Track and manage outstanding fee payments effectively.
- **Fee Variations & Adjustments:** Accommodate fee variations and make necessary adjustments seamlessly.
- **Feeslips:** Generate detailed and accurate feeslips for clear record-keeping.
- **Uncollected Fees:** Monitor and manage uncollected fees to improve collection rates.
- **Fee Analysis:** Gain insights into fee collection trends and optimize strategies.
- **Fee Details:** Access comprehensive details of all fees for transparency and accuracy.
- **Batch Processing:** Streamline fee transactions in bulk for efficiency.
    """,

    'author': "Dynexcel",
    'website': "https://www.dynexcel.com",

    'category': 'Dynexcel',
    'version': '17.0.0.2',
    'installable': True,
    'application': True,
    # any module necessary for this one to work correctly
    'depends': ['de_school','account','de_school_enrollment'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/fee_data.xml',
        'data/feeslip_sequence.xml',
        'data/ir_cron_data.xml',
        'data/account_data.xml',
        'views/fees_menu.xml',
        'views/fee_category_views.xml',
        'views/fee_rule_views.xml',
        'views/fee_struct_views.xml',
        'views/feeslip_input_type_views.xml',
        'views/feeslip_views.xml',
        'wizard/feeslip_by_students_views.xml',
        'views/feeslip_run_views.xml',
        'reports/feeslip_report_template.xml',
        'reports/feeslip_report.xml',
        'reports/feeslip_report_views.xml',
        'wizard/report_feeslip_xlsx_wizard_views.xml',
        'views/feeslip_schedule_views.xml',
        'wizard/save_xlsx_views.xml',
        'wizard/feeslip_schedule_wizard_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'license': 'LGPL-3',
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
