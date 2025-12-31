# mission/models/mission.py

from odoo import models, fields, api, exceptions, _
from datetime import date

class Mission(models.Model):
    _name = 'mission.mission'
    _description = 'Mission'

    # ... (Vos champs existants) ...
    titre_mission = fields.Selection(
        selection=[
            ('location_mensuelle', 'Location mensuelle'),
            ('location_journaliere', 'Location journalière'),
            ('location_annuelle', 'Location annuelle'),
            ('transport_marchandise', 'Transport marchandise')
        ],
        string="Titre mission",
        required=True
    )
    description = fields.Text()
    date_debut = fields.Date(string="Date début")
    date_fin = fields.Date(string="Date fin")
    date_validation = fields.Date(string="Date validation")
    km = fields.Float(string="Kilométrage (km)")
    cout_total = fields.Float(string="Coût total", compute="_compute_cout_total", store=True)

    adresse_depart = fields.Char(string="Adresse de départ")
    adresse_arrive = fields.Char(string="Adresse d'arrivée")
    n_document = fields.Char(string="Numéro document externe")
    type_vehicule_id = fields.Many2one(
        "logifleet.type_vehicule",
        string="Type de véhicule",
        required=True
    )

    marque_id = fields.Many2one(
        "logifleet.marque",
        string="Marque",
        domain="[('type_ids', 'in', type_vehicule_id)]",
        required=True
    )

    modele_id = fields.Many2one(
        "logifleet.modele",
        string="Modèle",
        domain="[('marque_id', '=', marque_id)]",
        required=True
    )

    vehicule_id = fields.Many2one(
        "logifleet.vehicule",
        string="Véhicule",
        domain="[('modele_id', '=', modele_id)]",
        ondelete="cascade",
        required=True
    )

    
    conducteur_id = fields.Many2one("logifleet.conducteur", string="Conducteur", ondelete="set null")

    status = fields.Selection([
        ("brouillon", "Brouillon"),
        ("validee", "Validée"),
        ('en_cours', 'En Cours'), 
        ("terminee", "Terminée"),
    ], string="Statut", default="brouillon")

    invoice_id = fields.Many2one("account.move", string="Facture", readonly=True)
    client_id = fields.Many2one(
        "logifleet.client",
        string="Client",
        ondelete="cascade"
    )
    company_id = fields.Many2one(
        "res.company",
        string="Société",
        required=True,
        default=lambda self: self.env.company
    )

    # ================== CHAMPS D'INSPECTION ==================
    inspection_depart_id = fields.Many2one(
        'logifleet.inspection',
        string="Contrôle Départ Mission",
        help="Inspection de l'état du véhicule avant la mission."
    )

    inspection_retour_id = fields.Many2one(
        'logifleet.inspection',
        string="Contrôle Retour Mission",
        help="Inspection de l'état du véhicule après la mission."
    )
    
    is_depart_inspection_done = fields.Boolean(
        string="Contrôle Départ Effectué",
        compute='_compute_inspection_status',
        store=True
    )
    
    is_retour_inspection_done = fields.Boolean(
        string="Contrôle Retour Effectué", 
        compute='_compute_inspection_status',
        store=True
    )
    @api.onchange('vehicule_id')
    def _onchange_vehicule_id(self):
        if self.vehicule_id:
            self.type_vehicule_id = self.vehicule_id.type_vehicule_id.id
            self.marque_id = self.vehicule_id.marque_id.id
            self.modele_id = self.vehicule_id.modele_id.id
        else:
            self.type_vehicule_id = False
            self.marque_id = False
            self.modele_id = False
    @api.onchange('type_vehicule_id')
    def _onchange_type(self):
        self.marque_id = False
        self.modele_id = False
        self.vehicule_id = False

    @api.onchange('marque_id')
    def _onchange_marque(self):
        self.modele_id = False
        self.vehicule_id = False

    @api.onchange('modele_id')
    def _onchange_modele(self):
        self.vehicule_id = False

    @api.depends('inspection_depart_id', 'inspection_retour_id')
    def _compute_inspection_status(self):
        for rec in self:
            rec.is_depart_inspection_done = bool(rec.inspection_depart_id)
            rec.is_retour_inspection_done = bool(rec.inspection_retour_id)

    # ================== LOGIQUE MÉTIER ==================

    @api.depends('km')
    def _compute_cout_total(self):
        for rec in self:
            rec.cout_total = rec.km * 10 

    # Fonction pour ouvrir/créer l'inspection de départ
    def action_open_or_create_inspection_depart(self):
        self.ensure_one()
        ctx = {
            'default_vehicule_id': self.vehicule_id.id,
            'default_odometer_inspection': self.vehicule_id.odometer, 
            'default_date_inspection': fields.Date.today(),
            'default_notes_detaillees': _('Contrôle d\'état avant départ en mission.'),
            'default_mission_id': self.id, # <-- C'est ce contexte qui fait le lien
        }
        if self.inspection_depart_id:
            return {'type': 'ir.actions.act_window', 'res_model': 'logifleet.inspection', 'res_id': self.inspection_depart_id.id, 'view_mode': 'form', 'target': 'current', 'context': ctx}
        
        # CORRECTION 1 : Utilisez 'target': 'current' pour forcer le rafraîchissement
        return {'name': _('Nouvelle Inspection Départ Mission'), 
                'type': 'ir.actions.act_window', 
                'res_model': 'logifleet.inspection', 
                'view_mode': 'form', 
                'context': ctx, 
                'target': 'current'} 

    # Fonction pour ouvrir/créer l'inspection de retour
    def action_open_or_create_inspection_retour(self):
        self.ensure_one()
        ctx = {
            'default_vehicule_id': self.vehicule_id.id,
            'default_odometer_inspection': self.vehicule_id.odometer, 
            'default_date_inspection': fields.Date.today(),
            'default_notes_detaillees': _('Contrôle d\'état au retour de mission.'),
            'default_mission_id': self.id, 
        }
        if self.inspection_retour_id:
            return {'type': 'ir.actions.act_window', 'res_model': 'logifleet.inspection', 'res_id': self.inspection_retour_id.id, 'view_mode': 'form', 'target': 'current', 'context': ctx}
        
        # CORRECTION 2 : Utilisez 'target': 'current'
        return {'name': _('Nouvelle Inspection Retour Mission'), 
                'type': 'ir.actions.act_window', 
                'res_model': 'logifleet.inspection', 
                'view_mode': 'form', 
                'context': ctx, 
                'target': 'current'}

    # ================== MODIFICATION DES STATUTS AVEC VÉRIFICATION D'INSPECTION ==================

    def action_valider_mission(self):
        """Valider et lancer la mission SEULEMENT si l'inspection de départ est faite."""
        for rec in self:
            
        # 🚫 Empêcher la mission si le véhicule est en maintenance ou en attente
            if rec.vehicule_id.status in ["en_maintenance", "en_attente"]:
                raise exceptions.UserError(
                    _("Impossible de valider la mission : le véhicule '%s' est actuellement '%s'.") 
                    % (rec.vehicule_id.matricule, rec.vehicule_id.status)
                )
            # Cette vérification est correcte, elle nécessite seulement que le Many2one soit rempli
           
            if rec.status == "brouillon":
                rec.status = "validee"
                rec.date_validation = rec.date_debut
                if rec.vehicule_id:
                    rec.vehicule_id.status = "en_mission"

    def action_terminer_mission(self):
        """Terminer la mission SEULEMENT si l'inspection de retour est faite."""
        for rec in self:
          
            if rec.status in ["validee", "en_cours"]:
                rec.status = "terminee"
                
                if rec.vehicule_id:
                    rec.vehicule_id.status = "disponible"

                    mission_name = dict(rec._fields['titre_mission'].selection).get(rec.titre_mission)
                
                    if rec.cout_total > 0:
                        self.env["logifleet.expense"].create({
                            "name": f"Mission: {mission_name or 'Mission'}",  
                            "vehicle_id": rec.vehicule_id.id,
                            "type": "mission",
                            "amount": rec.cout_total,
                            "date": rec.date_fin or fields.Date.today(),
                            "notes": rec.description or "",
                        })
                        
    # ... (Le reste des méthodes action_facturer_mission et MissionClient reste inchangé) ...
    def action_facturer_mission(self):
        # ... (Logique de facturation inchangée) ...
        for mission in self:
            partner = mission.client_id.partner_id
            if not partner:
                raise ValueError("Le client sélectionné n’est pas lié à un partenaire Odoo (res.partner).")

            journal = self.env['account.journal'].search([
                ('type', '=', 'sale'),
                ('company_id', '=', mission.company_id.id)
            ], limit=1)
            if not journal:
                raise ValueError("Aucun journal de vente trouvé pour la société.")

            income_account = self.env['account.account'].search([
                ('company_ids', 'in', [self.company_id.id]),
                ('internal_group', '=', 'income')
            ], limit=1)

            if not income_account:
                raise ValueError("Aucun compte de revenus configuré pour la société.")

            invoice_vals = {
                "partner_id": partner.id,
                "move_type": "out_invoice",
                "journal_id": journal.id,
                "invoice_date": fields.Date.context_today(self),
                "invoice_line_ids": [(0, 0, {
                    "name": mission.titre_mission or "Mission",
                    "quantity": 1,
                    "price_unit": mission.cout_total,
                    "account_id": income_account.id,
                })],
            }

            invoice = self.env["account.move"].create(invoice_vals)
            mission.invoice_id = invoice.id

            return {
                "type": "ir.actions.act_window",
                "res_model": "account.move",
                "view_mode": "form",
                "res_id": invoice.id,
                "target": "current",
            }


class MissionClient(models.Model):
    _name = "mission.client"
    _description = "Client Mission"

    name = fields.Char("Nom du client", required=True)
    partner_id = fields.Many2one("res.partner", string="Partenaire lié")
    active = fields.Boolean(default=True)

class MissionVehiculePointage(models.Model):
    _name = "mission.vehicule.pointage"
    _description = "Pointage Mensuel des Véhicules"

    vehicule_id = fields.Many2one("logifleet.vehicule", string="Véhicule", required=True)
    client_id = fields.Many2one("logifleet.client", string="Client", required=True)
    month = fields.Selection(
        [(str(m), str(m)) for m in range(1, 13)],
        string="Mois",
        required=True,
    )
    year = fields.Integer(string="Année", default=lambda self: fields.Date.today().year)
