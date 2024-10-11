{
    'name': 'siantou-core',
    'version': '1.0',
    'description': "Module de base de SIANTOU UNIV",
    'summary': "Module de base de SIANTOU UNIV",
    'author': 'Landry',
    'website': 'https://erplandry.net',
    'licence': 'LGPL-3',
    'category':'Education',
    'depends':[
        'base'
    ],
    'data':[
        'views/cycle_view.xml',
        'views/site_view.xml',
        'views/batiment_view.xml',
        'views/config_lot_view.xml',
        'views/matiere_view.xml',
        'views/salle_view.xml',
        'views/specialite_view.xml',
        'views/option_view.xml',
        'views/filiere_view.xml',
        'views/niveau_view.xml',
        'security/ir.model.access.csv',
    ],
    'images': [
        'static/description/siantou_preinscription_banner.jpg',
    ],
    'auto_install':False,
    'application':True,
    'sequence':'-10',
}