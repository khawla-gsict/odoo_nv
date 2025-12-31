# -*- coding: utf-8 -*-
# from odoo import http


# class Sinistre(http.Controller):
#     @http.route('/sinistre/sinistre', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sinistre/sinistre/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('sinistre.listing', {
#             'root': '/sinistre/sinistre',
#             'objects': http.request.env['sinistre.sinistre'].search([]),
#         })

#     @http.route('/sinistre/sinistre/objects/<model("sinistre.sinistre"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sinistre.object', {
#             'object': obj
#         })

