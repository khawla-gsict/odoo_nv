from odoo import models, fields, api, _
from datetime import date, timedelta
from dateutil import parser
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)
import requests


class Vehicule(models.Model):
    _name = "logifleet.vehicule"
    _description = "Véhicule"
    _rec_name = "matricule"

    # -----------------------------------------------------
    # IDENTITÉ
    # -----------------------------------------------------
    matricule = fields.Char(string="Matricule", required=True)
    num_serie = fields.Char(string="N° de série", required=True)
    annee = fields.Integer(string="Année", required=True)
    image = fields.Image("Image")

    # -----------------------------------------------------
    # INFOS TECHNIQUES
    # -----------------------------------------------------
    odometer = fields.Float(string="Kilométrage", tracking=True)
    affectation = fields.Selection([('interne', 'Interne'), ('externe', 'Externe')], string="Affectation")
    valeur_achete = fields.Float(string="Valeur d'achat")
    type_carburant = fields.Char(string="Type carburant")
    date_aquisition = fields.Date(string="Date d'acquisition")

    status = fields.Selection([
        ("disponible", "Disponible"),
        ("en_mission", "En mission"),
        ("en_attente_maintenance", "En attente de maintenance"),
        ("en_maintenance", "En maintenance"),
        ('en_attente', 'En attente'),
    ], string="Statut", default="disponible", compute='_compute_status_from_alert')

    n_chevaux = fields.Char(string="Chevaux fiscaux")
    num_immobilisation = fields.Char(string="N° immobilisation")
    pt_en_charge = fields.Char(string="PTAC")
    n_places = fields.Char(string="Places")
    designation = fields.Char(string="Désignation libre")

    # -----------------------------------------------------
    # RELATIONS
    # -----------------------------------------------------
    client_id = fields.Many2one("logifleet.client", string="Client",
                                ondelete="set null")
    type_vehicule_id = fields.Many2one("logifleet.type_vehicule", string="Type véhicule",
                                ondelete="set null")
    marque_id = fields.Many2one("logifleet.marque", string="Marque",
                                ondelete="set null")
    modele_id = fields.Many2one("logifleet.modele", string="Modèle",
                                ondelete="set null")

    fiche_controle_ids = fields.One2many("logifleet.fiche_controle", "vehicule_id", string="Fiches contrôle")
    historique_inspection_ids = fields.One2many("logifleet.inspection", "vehicule_id", string="Historique Inspections")
    derniere_inspection_id = fields.Many2one("logifleet.inspection", string="Dernière inspection", readonly=True)

    # -----------------------------------------------------
    # CHAMPS MIS À JOUR PAR FICHE CONTRÔLE **(readonly)**
    # -----------------------------------------------------
    odometer_derniere_maintenance = fields.Float(
        string="Km Dernière Maintenance",
        readonly=True
    )

    seuil_degradation_km = fields.Integer(
        string="Seuil de Dégradation (Km)",
        default=5000,
        readonly=True
    )

    prochain_changement_pneus_km = fields.Integer(
        string="Prochain changement pneus (Km)",
        readonly=True
    )

    pneu_interval_km = fields.Integer(
        string="Intervalle pneus alerte (Km)",
        default=1000,
        readonly=True
    )

    prochain_changement_accessoires_date = fields.Date(
        string="Prochain changement accessoires",
        readonly=True
    )

    prochain_maintenance_date = fields.Date(
        string="Prochaine maintenance",
        readonly=True
    )

    # -----------------------------------------------------
    # CHAMPS MIS À JOUR PAR INSPECTION (readonly)
    # -----------------------------------------------------
    etat_carrosserie = fields.Selection([
        ('intact', 'Intacte'),
        ('mineur', 'Dégâts mineurs'),
        ('majeur', 'Dégâts majeurs'),
    ], default='intact', readonly=True)

    etat_pneumatique = fields.Selection([
        ('ok', 'OK'),
        ('usure', 'Usure'),
        ('urgence', 'Changement urgent'),
    ], default='ok', readonly=True)

    etat_accessoires = fields.Selection([
        ('complet', 'Complets'),
        ('manquant', 'Manquants'),
        ('hs', 'HS'),
    ], default='complet', readonly=True)

    # -----------------------------------------------------
    # CHAMPS CALCULÉS
    # -----------------------------------------------------
    etat_general = fields.Selection([
     
        ('bon', 'Bon'),
        ('moyen', 'Moyen'),
        ('mauvais', 'Mauvais'),
    ], compute="_compute_etat_general_auto", store=True)

    maintenance_requise = fields.Boolean(
        string="Maintenance Requise",
        compute="_compute_maintenance_requise",
        store=True
    )
    _sql_constraints = [
        ('matricule_unique', 'unique(matricule)', 'Ce matricule existe déjà !')
    ]
    # Champ calculé pour la concaténation
    marque_modele = fields.Char(
        string='Marque/Modèle',
        compute='_compute_marque_modele',
        store=True  # Pour permettre la recherche et le tri
    )

    @api.depends('marque_id', 'modele_id')
    def _compute_marque_modele(self):
        for record in self:
            marque = record.marque_id.nom_marque if record.marque_id else ''
            modele = record.modele_id.nom_modele if record.modele_id else ''
            
            if marque and modele:
                record.marque_modele = f"{marque} - {modele}"
            elif marque:
                record.marque_modele = marque
            else:
                record.marque_modele = modele
    # NOUVELLE MÉTHODE ONCHANGE
    @api.onchange('modele_id')
    def _onchange_modele_id(self):
        """ Déduit la marque et le type si un modèle est choisi """
        if self.modele_id:
            # Déduire la Marque
            if not self.marque_id or self.marque_id != self.modele_id.marque_id:
                self.marque_id = self.modele_id.marque_id.id
            
            # Déduire le Type de Véhicule
            # S'il y a plusieurs types associés au modèle, nous prenons le premier.
            # Sinon, si la liste est vide, on ne change rien.
            types = self.modele_id.type_ids
            if types:
                if not self.type_vehicule_id or self.type_vehicule_id not in types:
                    self.type_vehicule_id = types[0].id
        else:
            # Si le modèle est effacé, on ne touche pas à la marque et au type,
            # car ils peuvent être nécessaires pour le filtre.
            pass
    # -------------------
    # Contrôle côté Python
    # -------------------
    @api.constrains('matricule')
    def _check_matricule_unique(self):
        for rec in self:
            if rec.matricule:
                duplicate = self.search([('matricule', '=', rec.matricule), ('id', '!=', rec.id)])
                if duplicate:
                    raise models.Validat
    odometer_last_update = fields.Datetime(string="Dernière mise à jour odomètre")

    # -----------------------------------------------------
    # CALCUL DE LA DERNIÈRE INSPECTION
    # -----------------------------------------------------
    fiche_controle_id = fields.Many2one(
        "logifleet.fiche_controle", string="Fiche de Contrôle", readonly=True,
                                ondelete="set null"
    )
    controle_administratif_ids = fields.One2many(
        'logifleet.controle_administratif',  # modèle enfant
        'vehicule_id',                        # champ Many2one sur enfant
        string="Contrôles Administratifs"
    )
    @api.model
    def create(self, vals):
        vehicule = super().create(vals)

        # Créer une fiche de contrôle vide
        fiche = self.env['logifleet.fiche_controle'].create({
            'vehicule_id': vehicule.id,
            'name': f"Fiche de contrôle {vehicule.matricule}",
            # On ne met pas les intervalles ni les dates
        })
        vehicule.fiche_controle_id = fiche.id

        # Retourner le véhicule créé
        return vehicule
    def action_open_fiche_controle(self):
        """Ouvrir la fiche de contrôle depuis le formulaire véhicule"""
        self.ensure_one()
        if not self.fiche_controle_id:
            raise UserError("Aucune fiche de contrôle associée à ce véhicule.")
        return {
            'name': "Fiche de Contrôle",
            'type': 'ir.actions.act_window',
            'res_model': 'logifleet.fiche_controle',
            'res_id': self.fiche_controle_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    def action_open_controles_admin(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': "Nouveau Contrôle Administratif",
            'res_model': 'logifleet.controle_administratif',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
            'context': {
                'default_vehicule_id': self.id,  # préremplit le véhicule
            },
        }

     # Champs pour les alertes
    next_assurance_date = fields.Date("Prochaine assurance")
    next_ct_date = fields.Date("Prochain contrôle technique")
    next_vignette_date = fields.Date("Prochaine vignette")
    

    # Historique des alertes
    alert_ids = fields.One2many('logifleet.alert', 'vehicule_id', string="Alertes")

    @api.depends('historique_inspection_ids', 'historique_inspection_ids.date_inspection')
    def _compute_derniere_inspection(self):
        for rec in self:
            last = rec.historique_inspection_ids.sorted(
                key=lambda x: (x.date_inspection, x.id),
                reverse=True
            )[:1]
            rec.derniere_inspection_id = last.id if last else False

    # -----------------------------------------------------
    # CALCUL ÉTAT GÉNÉRAL
    # -----------------------------------------------------
    @api.depends(
        'odometer', 'odometer_derniere_maintenance',
        'seuil_degradation_km', 'prochain_changement_pneus_km',
        'prochain_maintenance_date', 'prochain_changement_accessoires_date',
        'etat_carrosserie', 'etat_pneumatique', 'etat_accessoires'
    )
    def _compute_etat_general_auto(self):
        today = fields.Date.today()
        etat_map = {'bon': 'bon', 'bon': 'moyen', 'moyen': 'mauvais', 'mauvais': 'mauvais'}

        for rec in self:
            general_status = 'bon'

            if rec.date_aquisition and rec.date_aquisition.year == today.year:
                general_status = 'bon'

            # Dégradation progressive
            if rec.seuil_degradation_km > 0 and rec.odometer_derniere_maintenance:
                km_depuis = rec.odometer - rec.odometer_derniere_maintenance
                niveaux = int(km_depuis / rec.seuil_degradation_km)
                for _ in range(niveaux):
                    general_status = etat_map.get(general_status, general_status)

            # Conditions critiques
            if rec.etat_pneumatique == 'urgence' or rec.etat_carrosserie == 'majeur':
                general_status = 'mauvais'
            elif rec.etat_pneumatique == 'usure' or rec.etat_carrosserie == 'mineur':
                general_status = 'moyen'

            rec.etat_general = general_status

    # -----------------------------------------------------
    # MAINTENANCE REQUISE
    # -----------------------------------------------------
    @api.depends(
        'etat_general', 'odometer',
        'prochain_changement_pneus_km',
        'prochain_maintenance_date',
        'prochain_changement_accessoires_date'
    )
    def _compute_maintenance_requise(self):
        today = fields.Date.today()
        for rec in self:
            alert = False
            if rec.etat_general == 'mauvais':
                alert = True
            elif rec.prochain_changement_pneus_km and rec.odometer >= rec.prochain_changement_pneus_km:
                alert = True
            elif rec.prochain_maintenance_date and today >= rec.prochain_maintenance_date:
                alert = True
            elif rec.prochain_changement_accessoires_date and today >= rec.prochain_changement_accessoires_date:
                alert = True
            rec.maintenance_requise = alert

    # -----------------------------------------------------
    # ACTION : Ouvrir maintenance
    # -----------------------------------------------------
    def action_view_maintenance_alerte(self):
        self.ensure_one()
        return {
            'name': _('Nouvelle Maintenance'),
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance_vehicule.maintenance',
            'view_mode': 'form',
            'context': {
                'default_vehicule_id': self.id,
                'default_type_maintenance': 'corrective',
            },
        }
     
    # -----------------------------------------------------

    @api.model
    def update_odometer_from_api_par_matricule(self):
        api_key = "2B61B041-CBBF-4A0C-A1FE-D95BCA0E7510"
        api_url = f"https://services.geoflotte.com/getrealtime/{api_key}"

        try:
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            _logger.error("Erreur appel API: %s", e)
            return False

        if not data.get("success"):
            return False

        Vehicule = self.env['logifleet.vehicule']

        for record in data.get("recordset", []):
            matricule_api = record.get("Immatriculation")
            km = record.get("i2bKm") or record.get("Odometre")
            timestamp = record.get("tempsReel")

            if not matricule_api or km is None:
                continue

            vehicule = Vehicule.search(
                [('matricule', '=', matricule_api)],
                limit=1
            )

            if not vehicule:
                continue

            vals = {'odometer': km}

            if timestamp:
                dt = parser.isoparse(timestamp).replace(tzinfo=None)
                vals['odometer_last_update'] = dt

            vehicule.write(vals)


   # ... dans la classe Vehicule ...
    def generate_alerts(self):
        for veh in self:
            fiche = veh.fiche_controle_id
            alert_data = [
                # Utilisez la clé technique 'assurance' (minuscule)
                ('assurance', date.today() + timedelta(days=fiche.assurance_interval_days)), 
                ('ct', date.today() + timedelta(days=fiche.ct_interval_days)),
                ('vignette', date.today() + timedelta(days=fiche.vignette_interval_days)),
            ]
            for typ, next_date in alert_data:
                self.env['logifleet.alert'].create({
                    'vehicule_id': veh.id,
                    'type': typ, # Maintenant 'typ' est bien une clé technique ('assurance', 'ct', etc.)
                    'next_date': next_date,
                    'state': 'pending'
                })
# 
   
    # -----------------------------------------------------
    # CALCUL ALERTE IMMINENTE
    # -----------------------------------------------------
    alerte_imminente = fields.Boolean(
    string="Alerte imminente",
    compute="_compute_alerte_imminente",
    store=False
)

    @api.depends('alert_ids.next_date', 'alert_ids.state')
    def _compute_alerte_imminente(self):
        today = fields.Date.today()
        date_limite = today + timedelta(days=30)

        for veh in self:
            veh.alerte_imminente = any(
                alert.state == 'pending'
                and alert.next_date
                and alert.next_date <= date_limite
                for alert in veh.alert_ids
            )
    active_alert_count = fields.Integer(
            string="Nombre d'alertes actives",
            compute="_compute_active_alert_count",
            store=False,
        )

    @api.depends('alert_ids.state')
    def _compute_active_alert_count(self):
        for veh in self:
            veh.active_alert_count = len(
                veh.alert_ids.filtered(lambda a: a.state == 'pending')
            )
   # Dans la classe Vehicule

    @api.onchange('affectation')
    def _onchange_affectation(self):
            # Réinitialisation des champs pour éviter les valeurs résiduelles
            self.client_id = False
            self.valeur_achete = 0.0
            self.date_aquisition = False
    
            if self.affectation == 'interne':
                logifleet_company = self.env.company
                logifleet_partner = logifleet_company.partner_id
        
                # 1. Tenter de lier au Partenaire de la Compagnie si celui-ci est un Client existant
                client = False
                if logifleet_partner:
                    # Chercher si l'ID du Partenaire de la Compagnie existe dans logifleet.client
                    client = self.env['logifleet.client'].search([('id', '=', logifleet_partner.id)], limit=1)

                # 2. Si le client n'a pas été trouvé (car l'ID est invalide ou n'est pas un 'logifleet.client'), 
                #    on cherche par le nom de la compagnie pour plus de robustesse.
                if not client:
                    client = self.env['logifleet.client'].search([('name', '=', logifleet_company.name)], limit=1)
        
                self.client_id = client.id if client else False
     # Champ calculé affichant le résumé de l'alerte la plus proche / active
    alerte_detail = fields.Char(
        string="Alerte",
        compute="_compute_alerte_detail",
        store=False
    )

    alerte_alert_id = fields.Many2one(
        'logifleet.alert',
        string="Alerte liée (dernière)",
        compute="_compute_alerte_detail",
        store=False
    )
    @api.depends('alert_ids.state', 'alert_ids.next_date', 'alert_ids.type')
    def _compute_alerte_detail(self):
        """Affiche uniquement la première alerte imminente (proche ou échue) pour le véhicule."""
        Alert = self.env['logifleet.alert']
        today = fields.Date.today()
        date_limite = today + timedelta(days=30)  # seuil : 30 jours à venir

        for veh in self:
            # chercher la première alerte pending et proche
            alert = Alert.search([
                ('vehicule_id', '=', veh.id),
                ('state', '=', 'pending'),
                ('next_date', '!=', False),
                ('next_date', '<=', date_limite)
            ], order='next_date asc', limit=1)

            if not alert:
                veh.alerte_detail = False
                veh.alerte_alert_id = False
                continue

            veh.alerte_alert_id = alert

            # Map simple des libellés selon le type d'alerte
            type_labels = {
                'assurance': 'Assurance',
                'ct': 'Contrôle technique',
                'vignette': 'Vignette',
                'pneus': 'Changement pneus',
                'vidange': 'Vidange',
                'chaine_distribution': 'Chaîne de distribution',
                'maintenance': 'Maintenance',
            }

            label = type_labels.get(alert.type, alert.type or 'Alerte')

            maintenance_types = {'pneus', 'vidange', 'chaine_distribution', 'maintenance'}
            controle_types = {'assurance', 'ct', 'vignette'}

            when = f" (échéance: {fields.Date.to_string(alert.next_date)})" if alert.next_date else ""

            if alert.type in maintenance_types:
                veh.alerte_detail = f"Maintenance requise: {label}{when}"
            elif alert.type in controle_types:
                veh.alerte_detail = f"Contrôle: {label}{when}"
            else:
                veh.alerte_detail = f"{label}{when}" 
    def action_open_latest_alert(self):
            """Ouvre le formulaire de la dernière alerte pending du véhicule (si existe)."""
            self.ensure_one()
            Alert = self.env['logifleet.alert']
            alert = Alert.search([('vehicule_id', '=', self.id), ('state', '=', 'pending')], order='next_date asc', limit=1)
            if not alert:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'logifleet.alert',
                    'view_mode': 'form',
                    'view_id': False,
                    'target': 'current',
                    'context': {'default_vehicule_id': self.id},
                }
            return {
                'type': 'ir.actions.act_window',
                'name': 'Alerte',
                'res_model': 'logifleet.alert',
                'res_id': alert.id,
                'view_mode': 'form',
                'target': 'current',
            }
    
    @api.depends('alert_ids.state', 'alert_ids.next_date')
    def _compute_status_from_alert(self):
        """Met le véhicule en 'en_attente' uniquement si une alerte imminente est pending."""
        today = fields.Date.today()
        date_limite = today + timedelta(days=30)

        for veh in self:
            # Vérifie s'il existe au moins une alerte pending et proche
            alerte_proche = any(
                a.state == 'pending' and a.next_date and a.next_date <= date_limite
                for a in veh.alert_ids
            )
            if alerte_proche:
                veh.status = 'en_attente'
            else:
                if veh.status not in ['en_mission', 'en_maintenance']:
                    veh.status = 'disponible'

# ---------------------------------------------------------
# AUTRES MODELES ANNEXES
# ---------------------------------------------------------


class VehiculeImage(models.Model):
    _name = "logifleet.vehicule.image"
    vehicule_id = fields.Many2one("logifleet.vehicule", ondelete="cascade")
    image = fields.Binary("Image", attachment=True)
    description = fields.Char("Description")


class VehiculeAlert(models.Model):
    # AJOUT DE L'INHERITANCE POUR LE SUIVI D'ACTIVITÉ
    _name = "logifleet.alert"
    _description = "Alerte Véhicule"
    # Changer 'mail.thread.mixin' par 'mail.thread'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    vehicule_id = fields.Many2one('logifleet.vehicule', string="Véhicule",ondelete="cascade")
    
    type = fields.Selection([
        ('assurance', 'Assurance'),
        ('ct', 'Contrôle Technique'),
        ('vignette', 'Vignette'),
        ('pneus', 'Changement Pneus'),
        ('vidange', 'Vidange'),
        ('chaine_distribution', 'Chaîne de Distribution'),
        ('maintenance', 'Maintenance'),
    ], string="Type d'alerte", required=True)

    maintenance_id = fields.Many2one('logifleet.maintenance')
    controle_id = fields.Many2one('logifleet.controle_administratif')
    # next_date sert aussi de date d'échéance d'activité
    next_date = fields.Date(string="Prochaine échéance", required=True) 
    
    state = fields.Selection([
        ('pending', 'En attente'),
        ('done', 'Traité'),
    ], string="Statut", default='pending')
    
    # CHAMP POUR DÉTERMINER QUI DOIT TRAITER L'ALERTE/ACTIVITÉ
    activity_user_id = fields.Many2one(
        'res.users', 
        string="Responsable Alerte", 
        default=lambda self: self.env.user,
        help="Utilisateur chargé de traiter cette alerte."
    )
    
    # CHAMP LIÉ POUR L'INTÉGRATION DU MIXIN
    date_deadline = fields.Date(
        related='next_date',
        string="Date Limite d'Activité",
        store=True,
        readonly=False
    )

    # CHAMP CALCULÉ POUR L'AFFICHAGE DANS LES VUES
    activity_state = fields.Selection([
        ('planned', 'Prévue'),
        ('overdue', 'En retard'),
        ('today', 'Aujourd\'hui'),
        ('done', 'Traité')
    ], compute='_compute_activity_state', string="Statut d'Activité", store=False)


    @api.depends('next_date', 'state')
    def _compute_activity_state(self):
        """Détermine l'état de l'activité pour le badge visuel."""
        today = fields.Date.today()
        for rec in self:
            if rec.state == 'done':
                rec.activity_state = 'done'
            elif rec.next_date:
                if rec.next_date < today:
                    rec.activity_state = 'overdue'
                elif rec.next_date == today:
                    rec.activity_state = 'today'
                else:
                    rec.activity_state = 'planned'
            else:
                rec.activity_state = 'planned'
    
    def action_open_form(self):
        self.ensure_one()

        # Types liés à la Maintenance Préventive (pneus, vidange, chaîne_distribution)
        if self.type in ['pneus', 'vidange', 'chaine_distribution']:
            # Assurez-vous que le modèle est correct : maintenance_vehicule.maintenance
            return {
                'type': 'ir.actions.act_window',
                'name': 'Maintenance Préventive',
                'res_model': 'maintenance_vehicule.maintenance', # Modèle de maintenance
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'default_vehicule_id': self.vehicule_id.id,
                    # Le type de maintenance est le même que le type d'alerte
                    'default_type_maintenance': 'preventive',
                    'default_type': self.type, # Pour pré-remplir le champ type dans le formulaire de maintenance
                    'default_alert_id': self.id,
                }
            }

        # Types liés aux Contrôles Administratifs (assurance, ct, vignette)
        elif self.type in ['assurance', 'ct', 'vignette']:
            # Assurez-vous que le modèle est correct : logifleet.controle_administratif
            return {
                'type': 'ir.actions.act_window',
                'name': 'Contrôle Administratif',
                'res_model': 'logifleet.controle_administratif', # Modèle de contrôle administratif
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'default_vehicule_id': self.vehicule_id.id,
                    'default_type_controle': self.type, # Pour pré-remplir le champ type de contrôle
                    'default_alert_id': self.id,
                }
            }
        
        # Pour les autres types (ex: 'maintenance' générale), si besoin
        else:
            return {'warning': {'title': "Erreur", 'message': "Type d'alerte non géré pour l'ouverture du formulaire."}}

    def action_traiter_alerte(self):
        self.ensure_one()

        # --- Maintenance préventive ---
        if self.type in ['pneus', 'vidange', 'chaine_distribution']:

            return {
                'type': 'ir.actions.act_window',
                'name': "Maintenance Préventive",
                'res_model': 'maintenance_vehicule.maintenance',
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'default_vehicule_id': self.vehicule_id.id,
                    'default_type_maintenance': 'preventive',
                    'default_alert_id': self.id,
                }
            }

        # --- Contrôles administratifs ---
        if self.type in ['assurance', 'ct', 'vignette']:
            return {
                'type': 'ir.actions.act_window',
                'name': "Contrôle Administratif",
                'res_model': 'logifleet.controle',
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'default_vehicule_id': self.vehicule_id.id,
                    'default_type_controle': self.type,
                    'default_alert_id': self.id,
                }
        }

    def action_done(self):
        for rec in self:
            rec.state = 'done'

            # Fermer l’activité
            activities = self.env['mail.activity'].search([
                ('res_model', '=', 'logifleet.alert'),
                ('res_id', '=', rec.id),
                ('done', '=', False),
            ])
            activities.action_feedback(
                feedback=f"Alerte {rec.type} traitée le {fields.Date.today()}"
            )

            fiche = self.env['logifleet.fiche_controle'].search([
                ('vehicule_id', '=', rec.vehicule_id.id),
                ('state', '=', 'done')
            ], limit=1)
            if not fiche:
                continue

            # -----------------------------
            # ALERTES KM → reset compteur UNIQUEMENT
            # -----------------------------
            if rec.type == 'vidange':
                fiche.km_derniere_vidange = rec.vehicule_id.odometer

            elif rec.type == 'chaine_distribution':
                fiche.km_derniere_chaine_distribution = rec.vehicule_id.odometer

            elif rec.type == 'pneus':
                fiche.km_derniere_maintenance = rec.vehicule_id.odometer

            # -----------------------------
            # ALERTES DATE → recréer la suivante
            # -----------------------------
            else:
                interval_map = {
                    'assurance': fiche.interval_assurance_jours,
                    'ct': fiche.interval_visite_technique_jours,
                    'vignette': fiche.interval_vignette_jours,
                }

                interval_days = interval_map.get(rec.type)
                if interval_days:
                    next_date = fields.Date.today() + relativedelta(days=interval_days)

                    self.create({
                        'vehicule_id': rec.vehicule_id.id,
                        'type': rec.type,
                        'next_date': next_date,
                        'state': 'pending',
                        'activity_user_id': rec.activity_user_id.id,
                    }).activity_schedule(
                        activity_type_id=activities[:1].activity_type_id.id or 1,
                        summary=f"PROCHAINE ALERTE {rec.type.upper()} ({rec.vehicule_id.matricule})",
                        date_deadline=next_date,
                        user_id=rec.activity_user_id.id,
                    )

        return True

    def _generate_next_alert(self):
        """Après validation d'une alerte, génère la prochaine selon l'intervalle défini dans la fiche de contrôle."""
        for alert in self:
            fiche = self.env['logifleet.fiche_controle'].search([('vehicule_id', '=', alert.vehicule_id.id)], limit=1)
            if not fiche:
                continue

            # Déterminer le type et calculer la prochaine date
            if alert.type == 'assurance':
                next_date = date.today() + relativedelta(days=fiche.interval_assurance_jours)
                fiche.date_prochaine_assurance = next_date
            elif alert.type == 'ct':
                next_date = date.today() + relativedelta(days=fiche.interval_visite_technique_jours)
                fiche.date_prochaine_visite_technique = next_date
            elif alert.type == 'vignette':
                next_date = date.today() + relativedelta(days=fiche.interval_vignette_jours)
                fiche.date_prochaine_vignette = next_date
     
            elif alert.type == 'pneus':
                # Pour pneus basé sur le km
                next_date = None  # ou garder None et gérer dans check_alerts
                fiche.km_derniere_maintenance = fiche.km_vehicule

            # Créer la nouvelle alerte
            fiche._create_alert_and_activity(
                vehicule=fiche.vehicule_id,
                alert_type=alert.type,
                alert_date=next_date if next_date else date.today(),
                summary=f"Nouvelle alerte {alert.type} pour {fiche.vehicule_id.matricule}",
                user_id=alert.activity_user_id.id
            )

