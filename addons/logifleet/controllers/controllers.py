# -*- coding: utf-8 -*-
# from odoo import http


# class Logifleet(http.Controller):
#     @http.route('/logifleet/logifleet', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/logifleet/logifleet/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('logifleet.listing', {
#             'root': '/logifleet/logifleet',
#             'objects': http.request.env['logifleet.logifleet'].search([]),
#         })

#     @http.route('/logifleet/logifleet/objects/<model("logifleet.logifleet"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('logifleet.object', {
#             'object': obj
#         })

