# -*- coding: utf-8 -*-
{
    'name': "mission",

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
    'license': 'LGPL-3', 
    # any module necessary for this one to work correctly
    'depends': ['base', 'logifleet', 'account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'report/mission_order.xml',
        'report/mission_report.xml',
        'views/mission_view.xml',
        'views/pointage_views.xml',
        'report/timesheet_report.xml',
        'report/timesheet_report_template.xml',
        'views/menu_mission.xml',
    

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'images': ['static/description/icon.png'],

    "installable": True,
    "application": True,
}

