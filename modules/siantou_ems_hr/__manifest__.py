# -*- coding: utf-8 -*-
{
    'name': "SIANTOU - EMS HR App",

    'summary': "Module de gestion des ressources humaines",

    'description': """
        Ce module gère l'ensemble des ressources humaines
        * Gestion de l'organigramme
        * Gestion des dossiers du personnels
        * Gestion de la carrières du personnel
        * Gestion des congés et permissions
        * Reporting et statistiques
    """,

    'author': "ICCSOFT SA - Francesca MBOUEMBE",
    'website': "https://www.iccsoft.cm",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '17.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['hr'],

    # always loaded
    'data': [
        #security
        'security/ir.model.access.csv',
        
        #views
        'views/education/hr_education_equivalence_views.xml',
        'views/education/hr_education_domaine_views.xml',
        'views/education/hr_education_discipline_views.xml',
        'views/education/hr_education_diplome.xml',
        'views/education/hr_education_certificat.xml',
        
        'views/carriere/hr_carriere_affectation_views.xml',
        'views/carriere/hr_annul_licenciement.xml',
        'views/carriere/hr_annul_suspension.xml',
        'views/carriere/hr_carrier_licencier.xml',
        'views/carriere/hr_motif_licenciement.xml',
        
        
        'views/hr_employee_family.xml',
        'views/hr_employer_rang_views.xml',
        'views/hr_employe_type_sanction_views.xml',
        'views/hr_employee_fonction_views.xml',
        
        'views/hr_employee_views.xml',
        'views/hr_employer_rang_views.xml',
        'views/hr_employee_discipline_views.xml',
        
        # Menus de l'application
        'views/menu.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

