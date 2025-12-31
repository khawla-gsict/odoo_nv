from odoo import models, fields, api, exceptions, _
from datetime import date

class MaintenanceVehicule(models.Model):
    _name = "maintenance_vehicule.maintenance"
    _description = "Maintenance Véhicule"

    name = fields.Char(string="Référence", required=True, copy=False, readonly=True, default=lambda self: _('Nouveau'))
    
    type_maintenance = fields.Selection(
        [('preventive', 'Préventive'), ('corrective', 'Corrective')],
        string="Type de maintenance",
        required=True
    )
    date_maintenance = fields.Date(string="Date de création", default=fields.Date.context_today)
    date_debut = fields.Date(string="Date de début")
    date_fin = fields.Date(string="Date de fin")
    lieu = fields.Char(string="Lieu")
    note = fields.Text(string="Notes")

    vehicule_id = fields.Many2one(
        "logifleet.vehicule",
        string="Véhicule",
        required=True,
        ondelete="cascade"
    )

    piece_ids = fields.One2many(
        "maintenance_vehicule.piece.line",
        "maintenance_id",
        string="Pièces utilisées"
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Devise",
        required=True,
        default=lambda self: self.env.company.currency_id.id
    )

    cout_total = fields.Monetary(
        string="Coût total",
        compute="_compute_cout_total",
        store=True
    )

    picking_id = fields.Many2one(
        "stock.picking",
        string="Bon de Commande Interne",
        readonly=True,
        copy=False
    )

    purchase_order_id = fields.Many2one(
        "purchase.order",
        string="Demande d'achat liée",
        readonly=True,
        copy=False
    )
    
    odometer_validation = fields.Float(
        string="Km à la fin de la maintenance",
        readonly=True,
        copy=False,
    )
    
    status = fields.Selection([
        ("brouillon", "Brouillon"),
        ("en_attente_pieces", "En attente des pièces"),
        ("en_cours", "En cours"),
        ("terminee", "Terminée"),
    ], default="brouillon", string="Statut", required=True)
    
    inspection_depart_id = fields.Many2one(
    'logifleet.inspection',
    string="Contrôle Début Maintenance",
    ondelete='set null',  # ✅ important
    help="Inspection de l'état du véhicule avant la maintenance."
    )

    inspection_retour_id = fields.Many2one(
        'logifleet.inspection',
        string="Contrôle Fin Maintenance",
        ondelete='set null',  # ✅ important
        help="Inspection de l'état du véhicule après la maintenance."
    )


    is_depart_inspection_done = fields.Boolean(
        string="Contrôle Début Effectué",
        compute='_compute_inspection_status',
        store=True
    )

    is_retour_inspection_done = fields.Boolean(
        string="Contrôle Fin Effectué",
        compute='_compute_inspection_status',
        store=True
    )
    alert_id = fields.Many2one("logifleet.alert", string="Alerte liée")

    @api.depends('inspection_depart_id', 'inspection_retour_id')
    def _compute_inspection_status(self):
        for rec in self:
            # Relecture forcée pour les champs Many2one de l'inspection.
            # Normalement, le 'store=True' rend cette ligne optionnelle, mais elle est là pour la robustesse.
            rec.is_depart_inspection_done = bool(rec.inspection_depart_id)
            rec.is_retour_inspection_done = bool(rec.inspection_retour_id)

    # ================== LOGIQUE MÉTIER ==================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('maintenance.vehicule') or _('Nouveau')
        return super().create(vals_list)

    @api.depends("piece_ids.subtotal")
    def _compute_cout_total(self):
        for rec in self:
            rec.cout_total = sum(line.subtotal for line in rec.piece_ids)
            
    def action_open_or_create_inspection_depart(self):
        self.ensure_one()
        
        inspection = self.inspection_depart_id 

        if not inspection:
           inspection = self.env['logifleet.inspection'].create({
                'vehicule_id': self.vehicule_id.id,
                'notes_detaillees': _('Contrôle d\'état avant maintenance.'),
                'odometer_inspection': self.vehicule_id.odometer,
            })

            # 🔥 C'est ça qui manquait !
        self.inspection_depart_id = inspection.id
        inspection.maintenance_id = self.id
      
        
        ctx = {
            'default_vehicule_id': self.vehicule_id.id,
            'default_odometer_inspection': self.vehicule_id.odometer, 
            'default_date_inspection': fields.Date.today(),
            'default_notes_detaillees': _('Contrôle d\'état avant maintenance.'),
            'default_maintenance_id': self.id,
        }
    
        return {
            'name': _('Contrôle de Départ'),
            'type': 'ir.actions.act_window',
            'res_model': 'logifleet.inspection',
            'view_mode': 'form',
            'res_id': inspection.id,
            'target': 'current',
            'context': ctx,
        }

    def action_open_or_create_inspection_retour(self):
        self.ensure_one()

        if self.inspection_retour_id:
            return {
                'name': _('Contrôle de Retour'),
                'type': 'ir.actions.act_window',
                'res_model': 'logifleet.inspection',
                'view_mode': 'form',
                'res_id': self.inspection_retour_id.id,
                'target': 'current',
            }

        inspection = self.env['logifleet.inspection'].create({
            'vehicule_id': self.vehicule_id.id,
            'maintenance_id': self.id,
            'odometer_inspection': self.vehicule_id.odometer,
            'notes_detaillees': _("Contrôle après maintenance"),
        })

        return {
            'name': _('Nouvelle Inspection - Retour'),
            'type': 'ir.actions.act_window',
            'res_model': 'logifleet.inspection',
            'view_mode': 'form',
            'res_id': inspection.id,
            'target': 'current',
        }

    def action_demander_maintenance(self):
        self.ensure_one()
        if not self.piece_ids:
            raise exceptions.UserError(_("Veuillez ajouter les pièces nécessaires à la maintenance."))

        # 1. Trouver l'Entrepôt principal de la société (pour obtenir WHL)
        company = self.env.company
        
        # NOTE: On trouve l'entrepôt par son code 'WHL' ou le nom, 
        # car company.internal_warehouse_id peut générer l'AttributeError si le module 'stock' est mal chargé.
        warehouse = self.env['stock.warehouse'].search([
            ('code', '=', 'WHL'),
            ('company_id', '=', company.id)
        ], limit=1)
        
        if not warehouse:
             raise exceptions.UserError(_("L'entrepôt WHL n'a pas été trouvé pour la société %s. Vérifiez le code court de l'entrepôt ('WHL') et la société associée." % company.name))

        # 2. Récupérer les emplacements et le Type d'Opération de cet entrepôt (WHL)
        stock_location = warehouse.lot_stock_id           # WHL/Stock
        internal_picking_type = warehouse.int_type_id    # Logifleet: Transferts internes (WHL/INT)
        
        # Emplacement Destination (Consommation/Sortie)
        consumption_location = self.env.ref("stock.stock_location_customers", raise_if_not_found=False)

        if not stock_location or not internal_picking_type or not consumption_location:
            raise exceptions.UserError(_("Configuration de l'entrepôt ou des emplacements de stock invalide. Veuillez vérifier WHL et ses types d'opérations."))

        # 3. Traiter l'alerte
        if self.alert_id:
            self.alert_id.state = "done"
            self.alert_id._generate_next_alert()

        # 4. Création ou mise à jour du Transfert de Stock
        picking = self.picking_id
        if not picking:
            picking = self.env['stock.picking'].create({
                # Utiliser le Type d'Opération de l'entrepôt WHL pour le bon préfixe
                'picking_type_id': internal_picking_type.id, 
                'location_id': stock_location.id,
                'location_dest_id': consumption_location.id,
                'origin': self.vehicule_id.matricule or self.name,
                'company_id': company.id, # Clé pour la compatibilité société
            })
            self.picking_id = picking.id
        else:
            # S'assurer que le picking utilise les bons types (en cas de modification)
            picking.write({
                'picking_type_id': internal_picking_type.id,
                'location_id': stock_location.id,
                'location_dest_id': consumption_location.id,
                'company_id': company.id,
            })
            picking.move_ids.unlink()

        # 5. Création des mouvements
        moves_data = []
        for line in self.piece_ids:
            moves_data.append({
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_id.uom_id.id,
                'location_id': stock_location.id,
                'location_dest_id': consumption_location.id,
                'picking_id': picking.id,
                # NOTE: Laissez l'état vide ou 'draft', action_confirm() s'en charge.
            })

        self.env['stock.move'].create(moves_data)
        
        # 6. Confirmer le picking (déclenche le statut 'En attente')
        picking.action_confirm()

        # 7. Mise à jour des statuts
        self.status = "en_attente_pieces"
        if self.vehicule_id:
            self.vehicule_id.status = "en_attente"

        return {
            'name': _('Bon de Commande Interne (Transfert de Pièces)'),
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'res_id': picking.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
    def action_lancer_maintenance(self):
        self.ensure_one()
        rec = self.browse(self.id) 
        
        if rec.piece_ids:
            if not rec.picking_id:
                raise exceptions.UserError(_("Un Bon de Commande Interne doit être généré avant de lancer la maintenance."))
            if rec.picking_id.state != 'done':
                raise exceptions.UserError(_("Le Bon de Commande Interne n'a pas encore été validé."))
            # ❌ Date début obligatoire
        if not rec.date_debut:
            raise exceptions.UserError(
                _("Veuillez saisir la date de début de la maintenance dans le formulaire.")
            )
        
        rec.status = "en_cours"
        if rec.vehicule_id:
            rec.vehicule_id.write({
                'status': "en_maintenance",
               
            })
        return True
    # Fonction pour ouvrir/créer l'inspection de début
   
    def action_valider_maintenance(self):
        self.ensure_one()
        rec = self.browse(self.id)
         # ❌ Date fin obligatoire
        if not rec.date_fin:
            raise exceptions.UserError(
                _("Veuillez saisir la date de fin de la maintenance dans le formulaire.")
            )
        rec.status = "terminee"
    
        if rec.vehicule_id:
            rec.vehicule_id.write({
                'status': "disponible",
                # si odometer_validation renseigné mettre à jour km ultime maintenance
                'odometer_derniere_maintenance': rec.odometer_validation or rec.vehicule_id.odometer
            })

        return True
# Classe Pièce inchangée
class MaintenancePieceLine(models.Model):
    _name = "maintenance_vehicule.piece.line"
    _description = "Pièce utilisée dans la maintenance"

    maintenance_id = fields.Many2one(
        "maintenance_vehicule.maintenance",
        string="Maintenance",
        ondelete="cascade"
    )
    product_id = fields.Many2one(
            "product.product",
            string="Pièce",
            required=True,
            # 💡 CORRECTION : Inclure les produits stockables ('product') ET consommables ('consu')
            domain=[("type", "in", ["product", "consu"])] 
        )
    quantity = fields.Float(string="Quantité", default=1.0)
    prix_unitaire = fields.Float(
        related="product_id.standard_price",
        string="Prix unitaire (Coût)",
        readonly=True,
        store=True
    )
    subtotal = fields.Float(
        string="Sous-total",
        compute="_compute_subtotal",
        store=True
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id
    )


    @api.depends("quantity", "prix_unitaire")
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.quantity * rec.prix_unitaire