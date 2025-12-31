from odoo import models, fields
class Client(models.Model):
    _name = "logifleet.client"
    _description = "Client"
    name = fields.Char(string="Client", required=True, tracking=True)
    adresse = fields.Char(string="Adresse")
    type_client = fields.Char(string="Type client (interne/externe)")
    vehicules_ids = fields.One2many("logifleet.vehicule", "client_id", string="Vehicules")
    partner_id = fields.Many2one("res.partner", string="Partenaire lié")
