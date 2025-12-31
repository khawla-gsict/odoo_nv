# -*- coding: utf-8 -*-
{
    'name': "sinistre",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'fleet',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','logifleet'],

    # always loaded
    'data': [
         'security/ir.model.access.csv',
        'views/sinistre_views.xml',
        'views/indemnisation_views.xml',
        'views/menu_sinistre.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'images': ['static/description/icon.png'],

     "installable": True,
    "application": True,
}

