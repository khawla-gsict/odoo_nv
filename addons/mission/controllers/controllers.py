# -*- coding: utf-8 -*-
# from odoo import http


# class Mission(http.Controller):
#     @http.route('/mission/mission', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/mission/mission/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('mission.listing', {
#             'root': '/mission/mission',
#             'objects': http.request.env['mission.mission'].search([]),
#         })

#     @http.route('/mission/mission/objects/<model("mission.mission"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('mission.object', {
#             'object': obj
#         })

