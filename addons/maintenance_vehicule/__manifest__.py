# -*- coding: utf-8 -*-
{
    'name': "maintenance_vehicule",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Manufacturing/maintenance_vehicule',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base',"logifleet",'stock', 'purchase'],

    # always loaded
    'data': [
         "security/ir.model.access.csv",
        "views/maintenance_request_views.xml",
        "views/maintenance_menu.xml",
    ],
    'images': ['static/description/icon.png'],

    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
     "installable": True,
    "application": True,
}

