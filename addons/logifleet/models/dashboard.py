from odoo import models, api
from datetime import date

class LogifleetDashboard(models.AbstractModel):
    _name = 'logifleet.dashboard'
    _description = 'LogiFleet Dashboard'

    @api.model
    def get_kpis(self):
        Vehicule = self.env['logifleet.vehicule']
        Mission = self.env['mission.mission']
        Maintenance = self.env['maintenance_vehicule.maintenance']
        Sinistre = self.env['sinistre.sinistre']

        return {
            'total_vehicules': Vehicule.search_count([]),
            'vehicules_dispo': Vehicule.search_count([('status', '=', 'disponible')]),
            'vehicules_mission': Mission.search_count([('status', '=', 'en_cours')]),
            'vehicules_maintenance': Maintenance.search_count([('status', '=', 'en_cours')]),
          #  'sinistres_ouverts': Sinistre.search_count([('state', '!=', 'done')]),
        }
