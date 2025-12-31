from odoo import models, fields, api, SUPERUSER_ID
from openpyxl import load_workbook

class TypeVehicule(models.Model):
    _name = "logifleet.type_vehicule"
    _rec_name = "nom_type"  # <-- CORRECTION ICI
    nom_type = fields.Char(required=True)
    vehicule_ids = fields.One2many("logifleet.vehicule", "type_vehicule_id")
    marque_ids = fields.Many2many("logifleet.marque")
    modele_ids = fields.Many2many("logifleet.modele") # Permet de lister les modèles associés à ce type

class Marque(models.Model):
    _name = "logifleet.marque"
    _rec_name = "nom_marque" # <-- CORRECTION ICI
    nom_marque = fields.Char(required=True)
    type_ids = fields.Many2many("logifleet.type_vehicule")
    modele_ids = fields.One2many("logifleet.modele", "marque_id", string="Modèles")
class Modele(models.Model):
    _name = "logifleet.modele"
    _rec_name = "nom_modele"
    nom_modele = fields.Char(required=True)
    marque_id = fields.Many2one("logifleet.marque", string="Marque")
    type_ids = fields.Many2many(
        "logifleet.type_vehicule", 
        string="Compatible Types"
    )
    vehicule_ids = fields.One2many(
        "logifleet.vehicule", 
        "modele_id", # Doit pointer vers le champ Many2one correspondant sur logifleet.vehicule
        string="Véhicules de ce Modèle"
    )
    piece_ids = fields.Many2many(
        "product.product",
        "modele_piece_rel",
        "modele_id",
        "product_id",
        string="Pièces compatibles"
    )
