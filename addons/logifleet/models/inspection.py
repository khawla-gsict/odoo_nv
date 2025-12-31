
from odoo import models, fields, api, _

import logging



_logger = logging.getLogger(__name__)



class LogifleetInspection(models.Model):

    _name = 'logifleet.inspection'

    _description = 'Fiche de Contrôle Véhicule'



    # Champs de liaison

    mission_id = fields.Many2one('mission.mission', string="Mission Liée", ondelete='set null')

    maintenance_id = fields.Many2one('maintenance_vehicule.maintenance', string="Maintenance Liée", ondelete='set null')



    # Détails inspection

    inspecteur_id = fields.Many2one('res.users', string="Inspecteur", default=lambda self: self.env.user.id)

    etat_general = fields.Selection(

        [('bon', 'Bon état'), ('moyen', 'État moyen'), ('mauvais', 'Mauvais état')],

        string="État Général", default='bon', required=True

    )

    etat_carrosserie = fields.Selection(

        [('intact', 'Intacte'), ('rayures', 'Rayures'), ('bosses', 'Bosses'), ('dommage_majeur', 'Dommage majeur')],

        string="Carrosserie", default='intact', required=True

    )

    etat_pneumatique = fields.Selection(

        [('neuf', 'Neuf'), ('usure_legere', 'Usure légère'), ('ok', 'Usure moyenne'), ('a_remplacer', 'À remplacer')],

        string="Pneus", default='ok', required=True

    )

    etat_accessoires = fields.Selection(

        [('complet', 'Complet'), ('manquant_mineur', 'Manquant mineur'), ('manquant_majeur', 'Manquant majeur')],

        string="Accessoires", default='complet', required=True

    )



    name = fields.Char(string="Référence", required=True, copy=False, readonly=True, default='Nouveau')

    vehicule_id = fields.Many2one('logifleet.vehicule', string="Véhicule", required=True)

    odometer_inspection = fields.Float(string="Kilométrage")

    date_inspection = fields.Date(string="Date d'Inspection", default=fields.Date.context_today)

    notes_detaillees = fields.Text(string="Notes Détaillées")



    # AUTO SEQUENCE

    @api.model

    def create(self, vals):

        ins = super().create(vals)



        maintenance = ins.maintenance_id

        if not maintenance or not maintenance.id:

            return ins



        # Ici maintenance est valide

        # Tu peux lier d'autres infos si tu veux

        # maintenance.write({'inspection_depart_id': ins.id})



        return ins

    # Dans logifleet.inspection (action_update_odometer)
    def action_update_odometer(self):
        self.ensure_one()

        # 1. Mise à jour du Kilométrage du véhicule (logique indépendante)
        if self.vehicule_id and self.odometer_inspection:
            self.vehicule_id.write({'odometer': self.odometer_inspection})

        maintenance = self.maintenance_id 
    
        # 2. Logique de validation de la maintenance
        if maintenance:
        
            # 🔥 SOLUTION FINALE : 
            # Forcer la lecture des champs nécessaires de la maintenance pour éviter '_unknown'.
            # Nous lisons les IDs des deux inspections liées à la maintenance.
        
            # NOTE : Utiliser .read() sur un Recordset Recordset (et non un Recordset d'ID)
            # est sûr ici car nous sommes dans une transaction active.
            maint_data = maintenance.read(['inspection_retour_id', 'id']) 
        
            if maint_data and maint_data[0].get('inspection_retour_id'):
            
                # Si le dictionnaire maint_data contient l'ID de l'inspection de retour
                inspection_retour_id = maint_data[0]['inspection_retour_id'][0] 
            
                # Si l'ID de l'inspection actuelle est le même que l'inspection de retour de la maintenance
                if inspection_retour_id == self.id:
                    # C'est l'inspection de retour, donc on met à jour l'odomètre de validation de la maintenance
                    maintenance.odometer_validation = self.odometer_inspection

        return True
    # Cette méthode n'est plus nécessaire car le recalcul est forcé dans `update_etat_from_inspection`

    def action_appliquer_etat_vehicule(self):

        self.ensure_one()

        if self.vehicule_id:

             self.vehicule_id.update_etat_from_inspection(self.id)

        return True