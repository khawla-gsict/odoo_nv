# mission/models/pointage_wizard.py
from odoo import models, fields, api
from datetime import date, datetime, timedelta
import calendar
import io
import base64
try:
    import xlsxwriter
except Exception:
    xlsxwriter = None

class TimesheetWizard(models.TransientModel):
    _name = "mission.timesheet.wizard"
    _description = "Timesheet mensuel véhicules (rapport)"

    client_id = fields.Many2one("logifleet.client", string="Client", required=True)
    date_start = fields.Date(string="Date début", required=True, default=lambda self: date.today().replace(day=1))
    date_end = fields.Date(string="Date fin", required=True, default=lambda self: date.today())
    html_table = fields.Html(string="Aperçu Timesheet", readonly=True)
    export_file = fields.Binary(string="Fichier Excel", readonly=True)
    export_filename = fields.Char(string="Nom du fichier", readonly=True)

    def _get_period_range(self):
        """Retourne la période et le nombre de jours."""
        if not self.date_start or not self.date_end:
            raise UserError("Veuillez renseigner la période (date début et date fin).")
        first = self.date_start
        last = self.date_end
        last_day = (last - first).days + 1
        return first, last, last_day


    def _fetch_missions_in_period(self, client_id, date_start, date_end):
        Mission = self.env['mission.mission']
        domain = [
            ('client_id', '=', client_id.id),
            ('titre_mission', 'in', ['location_mensuelle', 'location_journaliere', 'location_annuelle']),
            ('date_debut', '<=', date_end),
            ('date_fin', '>=', date_start),
        ]
        missions = Mission.search(domain)
        return missions


    def _build_days_matrix(self, missions, date_start, date_end):
        """
        Retourne dict: (vehicule, conducteur) -> set(days)
        """
        matrix = {}
        days_range = (date_end - date_start).days + 1
        for m in missions:
            veh = m.vehicule_id
            conducteur = m.conducteur_id.nom if m.conducteur_id else ""
            if not veh:
                continue
            matricule = veh.matricule or ""
            modele = veh.modele_id.nom_modele if veh.modele_id else ""
            key = (veh.id, matricule, modele, conducteur)
            if key not in matrix:
                matrix[key] = set()
            # overlap
            start = max(m.date_debut, date_start)
            end = min(m.date_fin, date_end)
            for i in range((end - start).days + 1):
                day_index = (start - date_start).days + 1 + i  # jour relatif dans la période
                matrix[key].add(day_index)
        return matrix
    def generate_timesheet(self):
        self.ensure_one()
        date_start = self.date_start
        date_end = self.date_end
        missions = self._fetch_missions_in_period(self.client_id, date_start, date_end)
        matrix = self._build_days_matrix(missions, date_start, date_end)
        num_days = (date_end - date_start).days + 1

        html = [f"<h3>Pointage — {self.client_id.name or ''} — du {date_start} au {date_end}</h3>"]
        html.append('<table border="1" style="border-collapse:collapse;width:100%">')
        html.append("<thead><tr><th>Matricule</th><th>Modèle</th><th>Conducteur</th>")
        for i in range(num_days):
            real_date = (date_start + timedelta(days=i)).strftime("%d-%m")
            html.append(f"<th>{real_date}</th>")
        html.append("<th>Total</th></tr></thead><tbody>")

        for (veh_id, matricule,modele, conducteur) in sorted(matrix.keys(), key=lambda x: (x[1] or "", x[2] or "", x[0])):
            days = matrix[(veh_id, matricule, modele,  conducteur)]
            total = len(days)
            html.append(f"<tr><td>{matricule}</td><td>{modele}</td><td>{conducteur}</td>")
            for d in range(1, num_days+1):
                html.append(f"<td style='text-align:center'>{'✓' if d in days else ''}</td>")
            html.append(f"<td style='text-align:center;font-weight:bold'>{total}</td></tr>")

        if not matrix:
            html.append(f"<tr><td colspan='{num_days+2}'>Aucun véhicule en location pour cette période</td></tr>")

        html.append("</tbody></table>")

        self.html_table = "".join(html)
        # Ne rien retourner ! ⚠️

    def action_export_xlsx(self):
        self.ensure_one()
        if xlsxwriter is None:
            raise UserError("xlsxwriter python package is requis sur le serveur.")

        first, last, last_day = self._get_period_range()
        missions = self._fetch_missions_in_period(self.client_id, first, last)
        matrix = self._build_days_matrix(missions, first, last)
    
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = workbook.add_worksheet("Timesheet")

        # Formats
        title_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 14})
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter',
                                             'bg_color': '#4F81BD', 'font_color': 'white', 'border': 1})
        cell_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
        tick_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#C6EFCE'})
        signature_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter'})

        # Title
        ws.merge_range(0, 0, 0, last_day+2, f"Timesheet — {self.client_id.name or ''} — du {first} au {last}", title_format)

        # Header
        start_row = 2
        ws.write(start_row, 0, "Matricule", header_format)
        ws.write(start_row, 1, "Modèle", header_format)
        ws.write(start_row, 2, "Conducteur", header_format)
        for i in range(last_day):
            ws.write(start_row, i+3, (first + timedelta(days=i)).strftime("%d-%m"), header_format)
        ws.write(start_row, last_day+3, "Total", header_format)


        # Rows
        row = start_row + 1
        for (veh_id, matricule,modele, conducteur) in sorted(matrix.keys(), key=lambda x: (x[1] or "", x[2] or "", x[0])):
            days = matrix[(veh_id, matricule, modele, conducteur)]
            ws.write(row, 0, matricule or f"#{veh_id}", cell_format)
            ws.write(row, 1, modele, cell_format)
            ws.write(row, 2, conducteur, cell_format)
            total = 0
            for d in range(1, last_day+1):
                col = d + 2  # Matricule=0, Modèle=1, Conducteur=2
                if d in days:
                    ws.write(row, col, "✓", tick_format)
                    total += 1
                else:
                    ws.write(row, col, "", cell_format)
            ws.write(row, last_day+3, total, cell_format)

            row += 1

        if not matrix:
            ws.merge_range(row, 0, row, last_day+2, "Aucun véhicule en location pour cette période.", cell_format)
            row += 1

        # Signatures en bas
        row += 2
        ws.merge_range(row, 0, row, (last_day+2)//2, "Signature Client:", signature_format)
        ws.merge_range(row, (last_day+2)//2+1, row, last_day+2, "Signature Responsable:", signature_format)

        workbook.close()
        output.seek(0)
        self.export_file = base64.b64encode(output.read())
        self.export_filename = f"timesheet_{self.client_id.name or 'client'}_{first}_{last}.xlsx"

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/?model=mission.timesheet.wizard&field=export_file&id={self.id}&filename={self.export_filename}&download=true",
            'target': 'self',
        }


    def action_export_pdf(self):
        self.ensure_one()

        first, last, last_day = self._get_period_range()
        missions = self._fetch_missions_in_period(self.client_id, first, last)
        matrix = self._build_days_matrix(missions, first, last)

        matrix_list = []
        for (veh_id, matricule,modele, conducteur), days in matrix.items():
            matrix_list.append({
                'veh_id': veh_id,
                'matricule': matricule,
                'modele': modele,
                'conducteur': conducteur,
                'days': sorted(list(days)),
                'total': len(days)
            })

        # 🔥 Liste des dates réelles (24-11, 25-11, ...)
        dates_display = [
            (first + timedelta(days=i)).strftime("%d-%m")
            for i in range(last_day)
        ]

        data = {
            'client': self.client_id.name if self.client_id else '',
            'date_start': first.strftime("%d-%m-%Y"),
            'date_end': last.strftime("%d-%m-%Y"),
            'last_day': last_day,
            'dates': dates_display,
            'matrix': matrix_list,
        }

        return self.env.ref("mission.timesheet_pdf_report").report_action(self, data={'data': data})



