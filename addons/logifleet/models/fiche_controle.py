from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date
from dateutil.relativedelta import relativedelta

class FicheControle(models.Model):
    _name = "logifleet.fiche_controle"
    _description = "Fiche de Contrôle Véhicule"

    vehicule_id = fields.Many2one(
        'logifleet.vehicule', string="Véhicule", required=True, ondelete="cascade"
    )
    name = fields.Char(string="Nom", required=True)

    # Intervalles à remplir par l'utilisateur
    interval_pneus_km = fields.Integer(string="Changer pneus tous les (Km)")
    interval_assurance_jours = fields.Integer(string="Renouveler assurance tous les (jours)")
    interval_visite_technique_jours = fields.Integer(string="Visite technique tous les (jours)")
    interval_vignette_jours = fields.Integer(string="Vignette tous les (jours)")
    interval_vidange_km = fields.Integer(string="Vidange tous les (Km)")
    interval_chaine_distribution_km = fields.Integer(string="Chaine de distribution tous les (Km)")

    # Champs calculés automatiquement
    date_prochaine_maintenance = fields.Date(string="Prochaine maintenance")
    date_prochaine_assurance = fields.Date(string="Prochaine assurance")
    date_prochaine_visite_technique = fields.Date(string="Prochaine visite technique")
    date_prochaine_vignette = fields.Date(string="Prochaine vignette")
    km_derniere_vidange = fields.Float(string="KM dernière vidange", default=0.0)
    km_derniere_chaine_distribution = fields.Float(string="KM dernière chaine", default=0.0)


    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Validé')
    ], string="Statut", default='draft', readonly=True)

    km_derniere_maintenance = fields.Float(string="KM dernière Maintenance", default=0.0)
    km_vehicule = fields.Float(related='vehicule_id.odometer', string="KM Actuel", readonly=True)

    # ------------------------
    # CREATE: juste créer la fiche vide
    # ------------------------
    @api.model
    def create(self, vals):
        res = super().create(vals)
        # La fiche est vide, prête à être remplie par l'utilisateur
        return res

    # ------------------------
    # VALIDATION DE LA FICHE
    # ------------------------
    def action_valider(self):
        for rec in self:
            # Vérifier que tous les intervalles sont remplis
            required_fields = [
                'interval_assurance_jours', 'interval_visite_technique_jours',
                'interval_vignette_jours', 'interval_vidange_km',
                'interval_chaine_distribution_km', 'interval_pneus_km'
            ]
            for field in required_fields:
                if not getattr(rec, field):
                    raise UserError("Veuillez remplir tous les intervalles avant de valider.")
            
            rec.state = 'done'

            # Calculer les dates de la prochaine alerte
            rec.date_prochaine_assurance = fields.Date.today() + relativedelta(days=rec.interval_assurance_jours)
            rec.date_prochaine_visite_technique = fields.Date.today() + relativedelta(days=rec.interval_visite_technique_jours)
            rec.date_prochaine_vignette = fields.Date.today() + relativedelta(days=rec.interval_vignette_jours)


            # Créer les alertes via la fonction utilitaire
            rec._create_alert_and_activity(rec.vehicule_id, 'assurance', rec.date_prochaine_assurance, f"Alerte Assurance {rec.vehicule_id.matricule}", self.env.user.id)
            rec._create_alert_and_activity(rec.vehicule_id, 'ct', rec.date_prochaine_visite_technique, f"Alerte Contrôle Technique {rec.vehicule_id.matricule}", self.env.user.id)
            rec._create_alert_and_activity(rec.vehicule_id, 'vignette', rec.date_prochaine_vignette, f"Alerte Vignette {rec.vehicule_id.matricule}", self.env.user.id)
         
    # ------------------------
    # UTILITAIRE: créer alerte + activité
    # ------------------------
    def _create_alert_and_activity(self, vehicule, alert_type, alert_date, summary, user_id):
        alert_obj = self.env['logifleet.alert']
        ActivityToDo = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        activity_type_id = ActivityToDo.id if ActivityToDo else 1
        
        existing_alert = alert_obj.search([
            ('vehicule_id', '=', vehicule.id),
            ('type', '=', alert_type),
            ('state', '=', 'pending')
        ], limit=1)
        
        if not existing_alert:
            nouvelle_alerte = alert_obj.create({
                'vehicule_id': vehicule.id,
                'type': alert_type,
                'next_date': alert_date,
                'state': 'pending',
                'activity_user_id': user_id, 
            })
            nouvelle_alerte.activity_schedule(
                activity_type_id=activity_type_id,
                summary=summary,
                date_deadline=alert_date,
                user_id=user_id,
            )
            return True
        return False

    # ------------------------
    def write(self, vals):
        for rec in self:
            # Autoriser modification si état draft
            if rec.state == 'done' and any(k in vals for k in [
                'interval_pneus_km',
                'interval_assurance_jours',
                'interval_visite_technique_jours',
                'interval_vignette_jours',
                'interval_vidange_km',
                'interval_chaine_distribution_km'
            ]):
                raise UserError("Cette fiche est validée et ne peut plus être modifiée.")
        return super().write(vals)

    # ------------------------
    # Vérification périodique des alertes
    # ------------------------
    @api.model
    def check_alerts(self):
        today = fields.Date.today()
        fiches = self.search([('state', '=', 'done')])
        cron_user = self.env.ref('base.user_admin')

        for f in fiches:
            vehicule = f.vehicule_id
            km_actuel = vehicule.odometer or 0.0

            # -------- ALERTES KM --------
            if f.interval_pneus_km and (km_actuel - f.km_derniere_maintenance) >= f.interval_pneus_km:
                f._create_alert_and_activity(
                    vehicule, 'pneus', today,
                    f"ALERTE KM : Changement pneus requis ({vehicule.matricule})",
                    cron_user.id
                )

            if f.interval_vidange_km and (km_actuel - f.km_derniere_vidange) >= f.interval_vidange_km:
                f._create_alert_and_activity(
                    vehicule, 'vidange', today,
                    f"ALERTE KM : Vidange requise ({vehicule.matricule})",
                    cron_user.id
                )

            if f.interval_chaine_distribution_km and (
                km_actuel - f.km_derniere_chaine_distribution
            ) >= f.interval_chaine_distribution_km:
                f._create_alert_and_activity(
                    vehicule, 'chaine_distribution', today,
                    f"ALERTE KM : Chaîne de distribution à vérifier ({vehicule.matricule})",
                    cron_user.id
                )

            # -------- ALERTES DATE --------
            date_alerts = [
                ('assurance', f.date_prochaine_assurance, "Assurance à renouveler"),
                ('ct', f.date_prochaine_visite_technique, "Contrôle technique requis"),
                ('vignette', f.date_prochaine_vignette, "Vignette à renouveler"),
            ]

            for alert_type, alert_date, label in date_alerts:
                if alert_date and alert_date <= today:
                    f._create_alert_and_activity(
                        vehicule, alert_type, alert_date,
                        f"ALERTE DATE : {label} ({vehicule.matricule})",
                        cron_user.id
                    )



class ControleAdministratif(models.Model):
    _name = "logifleet.controle_administratif"
    _description = "Controle Assurance / CT / Vignette"

    vehicule_id = fields.Many2one('logifleet.vehicule', string="Véhicule", required=True,ondelete="cascade")
    type_controle = fields.Selection([
        ('assurance','Assurance'),
        ('ct','Contrôle Technique'),
        ('vignette','Vignette')
    ], string="Type de contrôle", required=True)
    
    date_controle = fields.Date(string="Date", required=True)
    montant = fields.Float(string="Montant")
    informations = fields.Text(string="Informations supplémentaires")
    state = fields.Selection([('draft','Brouillon'),('done','Validé')], default='draft', readonly=True)
    alert_id = fields.Many2one("logifleet.alert", string="Alerte liée")

    # ✅ Champ computed pour afficher tous les contrôles du véhicule
    historique_controles_ids = fields.One2many(
    'logifleet.controle_administratif',
    'vehicule_id',
    string="Historique des contrôles",
    compute='_compute_historique_controles'
)

    @api.depends('vehicule_id')
    def _compute_historique_controles(self):
        for rec in self:
            if rec.vehicule_id:
                rec.historique_controles_ids = rec.vehicule_id.controle_administratif_ids.filtered(lambda x: x.id != rec.id)
            else:
                rec.historique_controles_ids = False
    def action_valider(self):
            for rec in self:
                if rec.state == 'done':
                    continue  # éviter double validation
                rec.state = 'done'

                # 1️⃣ Mettre l'alerte existante en done
                alerts = self.env['logifleet.alert'].search([
                    ('vehicule_id', '=', rec.vehicule_id.id),
                    ('type', '=', rec.type_controle),
                    ('state', '=', 'pending')
                ])
                alerts.write({'state': 'done'})

                # 2️⃣ Si le contrôle est lié à une alerte, générer la prochaine alerte
                if rec.alert_id:
                    rec.alert_id.state = "done"
                    if hasattr(rec.alert_id, '_generate_next_alert'):
                        rec.alert_id._generate_next_alert()
