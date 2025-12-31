# -*- coding: utf-8 -*-
# from odoo import http


# class MaintenanceVehicule(http.Controller):
#     @http.route('/maintenance_vehicule/maintenance_vehicule', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/maintenance_vehicule/maintenance_vehicule/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('maintenance_vehicule.listing', {
#             'root': '/maintenance_vehicule/maintenance_vehicule',
#             'objects': http.request.env['maintenance_vehicule.maintenance_vehicule'].search([]),
#         })

#     @http.route('/maintenance_vehicule/maintenance_vehicule/objects/<model("maintenance_vehicule.maintenance_vehicule"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('maintenance_vehicule.object', {
#             'object': obj
#         })

