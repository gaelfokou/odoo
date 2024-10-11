{
    'name': 'siantou management',
    'version': '1.0',
    'description': 'This module allow to manage school',
    'summary': 'This module allow to manage school',
    'author': 'Landry',
    'website': 'https://erplandry.net',
    'licence': 'LGPL-3',
    'category':'Education',
    'depends':[
        'base'
    ],
    'data':[
        'views/site_view.xml',
        'views/batiment_view.xml',
        'views/config_lot_view.xml',
        'views/matiere_view.xml',
        'views/salle_view.xml',
        'views/specialite_view.xml',
        'views/option_view.xml',
        'views/filiere_view.xml',
        'security/ir.model.access.csv',
    ],
    'auto_install':False,
    'application':False,
    'sequence':'0',
}