{
    'name': "logifleet",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
            Vue d'ensemble en temps réel de vos véhicules, chauffeurs, dépenses et maintenances
    """,

    'author': "LogiFleet",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Field Service',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','web','stock','mail'],
 
    'assets': {
        'web.assets_backend': [
            'logifleet/static/src/js/dashboard.js',
            "logifleet/static/src/xml/dashboard.xml",
            'logifleet/static/src/css/vehicule_alert.css',
        ],
  
    },
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'data/cron_jobs.xml',# <-- NOUVEAU
        'views/inspection_views.xml',
        'views/controle_administratif.xml',
        'views/fiche_controle_views.xml',
       

        'views/vehicule_views.xml',
        'views/client_views.xml',
        'views/type_models.xml',
        'views/conducteur_views.xml',
        'views/logifleet_expense_views.xml',
        'views/parc_auto.xml',
        'views/menu.xml',
         'views/dashboard_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'images': ['static/description/icon.png'],

    "installable": True,
    "application": True,
}

