# -*- coding: utf-8 -*-
{
    "name": "Paiements étudiant(e)s",
    "version": '1.0',
    "author": "ICC SOFT S.A",
    "category": 'Scolarité',
    "company": "ICC SOFT S.A",
    "website": "http://www.iccsoft.com",
    'summary': 'Manage students fee',
    'description': """Manage students fee""",
    "depends": ['base', 'account', 'siantou_ems_core'],
    "data": [
        'data/account_data.xml',
        'data/sequences.xml',
        # 'data/cron.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/fee_menu_view.xml',
        # 'views/fee_register.xml',
        'views/fee_structure.xml',
        'views/fee_structure_line.xml',
        'views/fee_types.xml',
        'views/fee_category.xml',
        'views/fee_journal_dashboard_view.xml',
        'views/fee_journal_inherit.xml',
        # 'views/fee_student.xml',
        'views/fee_payment.xml',
        'views/fee_payment_enrollment.xml',
        'views/fee_moratoire.xml',
        'views/fee_special.xml',
        'views/fee_bank_account_setting.xml',

        # 'views/education_fee_classe_views.xml',
        # 'wizard/frais_etudiant.xml',
        'wizard/complet_paiement_wizard.xml',

        # report
        
        # "reports/report_list_factures.xml",
        "reports/report_student_fees.xml",
        # "reports/report.xml",

    ],
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    "installable": True,
    "auto_install": False,
    'application': True,
}
