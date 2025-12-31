from odoo import models, fields,api
class DemandeIndemnisation(models.Model):
    _name = 'sinistre.indemnisation'
    _description = 'Demande Indemnisation'

    sinistre_id = fields.Many2one("sinistre.sinistre", string="Sinistre", ondelete="cascade")
    type_assurance = fields.Selection([
        ('rc', 'Responsabilité civile'),
        ('tout_risque', 'Tous risques'),
        ('autre', 'Autre')
    ], string="Type assurance", required=True)

    montant_demande = fields.Float(string="Montant demandé")
    montant_rembourse = fields.Float(string="Montant remboursé")
    statut = fields.Selection([
        ('en_attente', 'En attente'),
        ('rembourse', 'Remboursé'),
        ('refuse', 'Refusé')
    ], string="Statut", default="en_attente")

    rapport_expert = fields.Binary("Rapport expert")
    rapport_filename = fields.Char("Nom du fichier")

    cloture = fields.Boolean(
        string="Clôturé", compute="_compute_cloture", store=True
    )

    @api.depends('montant_rembourse', 'montant_demande')
    def _compute_cloture(self):
        for rec in self:
            rec.cloture = bool(rec.montant_rembourse and rec.montant_rembourse >= rec.montant_demande)
