from odoo import fields , models 
class Conducteur(models.Model):
    _name = "logifleet.conducteur"
    _description = "Conducteur"
    _rec_name = "nom" 
    nom = fields.Char(string="Nom", required=True)
    adresse = fields.Char(string="Adresse")
    num_permis = fields.Char(string="Numero de permis")
    type_permis = fields.Selection(selection=[('B','B'),('C','C'),('D','D')], default='B')
    disponibilite = fields.Char(string="Disponibilte  conducteur")
    status = fields.Char(string="Statu")
