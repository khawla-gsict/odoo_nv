# -*- coding: utf-8 -*-
from odoo import models, fields, api

class Sinistre(models.Model):
    _name = 'sinistre.sinistre'
    _description = 'Sinistre'

    type_sinistre = fields.Selection(
        string="Type sinistre",
        selection=[
            ('accident', 'Accident de la route'),
            ('vol', 'Vol'),
            ('incendie', 'Incendie'),
            ('dommage', 'Dommage matériel'),
            ('inondation', 'Inondation'),
            ('vandalisme', 'Vandalisme'),
            ('autre', 'Autre')
        ],
        default='accident'
    )
    lieu = fields.Char(string="Lieu")
    designation = fields.Char(string="Désignation")
    date_sinistre = fields.Date(string="Date du Sinistre")
    date_mis_en_service = fields.Date(string="Date de Mise en Service")
    nb_blesses = fields.Integer(string="Nombre de Blessés")
    description = fields.Text(string="Description")
    perturbation_humaine = fields.Boolean(string="Perturbation Humaine")

    vehicule_id = fields.Many2one(
        "logifleet.vehicule",
        string="Véhicule",
        ondelete="cascade"
    )
    conducteur_id = fields.Many2one(
        "logifleet.conducteur",
        string="Conducteur",
        ondelete="set null"
    )

    # Relation indemnisation
    demande_indemnisation_id = fields.One2many(
        "sinistre.indemnisation", "sinistre_id", string="Demandes d’indemnisation"
    )
