from odoo import models, fields, api

class LogifleetExpense(models.Model):
    _name = 'logifleet.expense'
    _description = 'Dépense véhicule'
    _order = 'date desc'

    name = fields.Char("Description", required=True)
    vehicle_id = fields.Many2one("logifleet.vehicule", string="Véhicule", required=True)
    type = fields.Selection([
        ('maintenance', 'Maintenance'),
        ('mission', 'Mission'),
        ('carburant', 'carburant'),
        ('assurance', 'assurance'),
        ('controle technique', 'controle technique'),
        ('autre', 'Autre'),
    ], string="Type", required=True)
    date = fields.Date("Date", default=fields.Date.today)
    amount = fields.Monetary("Montant", required=True)
    notes = fields.Text("Remarques")

    company_id = fields.Many2one('res.company', string="Société", default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string="Devise", default=lambda self: self.env.company.currency_id)
