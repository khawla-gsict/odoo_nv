from odoo import http
from odoo.http import request

class DashboardController(http.Controller):

    @http.route('/logifleet/dashboard/data', type='json', auth='user')
    def dashboard_data(self):
        vehicules = request.env['logifleet.vehicule'].read_group(
            [], ['id'], ['type_vehicule_id']
        )
        depenses = request.env['logifleet.maintenance'].read_group(
            [], ['valeur:sum'], ['date']
        )
        return {
            'vehicules': vehicules,
            'depenses': depenses,
        }
