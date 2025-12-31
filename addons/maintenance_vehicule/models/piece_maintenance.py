from odoo  import models, fields, api 
class MaintenancePiece(models.Model):
    _name = "maintenance_vehicule.piece"
    _description = "Pièces utilisées pour maintenance"

    maintenance_id = fields.Many2one("maintenance_vehicule.maintenance", string="Maintenance", required=True)
    product_id = fields.Many2one("product.product", string="Pièce", required=True, domain=[("detailed_type", "=", "product")])
    quantity = fields.Float(string="Quantité", required=True, default=1)
    prix_unitaire = fields.Float(
        string="Prix unitaire",
        related="product_id.standard_price",
        readonly=True,
        store=True
    )   
    subtotal = fields.Monetary(string="Sous-total", compute="_compute_subtotal", store=True)
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)

    @api.depends("quantite", "prix_unitaire")
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.quantite * rec.prix_unitaire

    def action_consume_stock(self):
        """Créer un mouvement de stock pour consommer les pièces utilisées"""
        for rec in self:
            if rec.quantite <= 0:
                continue

            # Prend l’emplacement "Stock" de l’entreprise
            stock_location = self.env.ref("stock.stock_location_stock")
            usage_location = self.env.ref("stock.stock_location_customers")  # sortie fictive

            self.env["stock.move"].create({
                "name": f"Utilisation {rec.product_id.display_name} pour maintenance {rec.maintenance_id.id}",
                "product_id": rec.product_id.id,
                "product_uom_qty": rec.quantite,
                "product_uom": rec.product_id.uom_id.id,
                "location_id": stock_location.id,
                "location_dest_id": usage_location.id,
                "state": "confirmed",
            })._action_done()
