/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

export class ParcDashboard extends Component {
    setup() {
        super.setup();
        this.loadData();
    }

    async loadData() {
        const data = await this.rpc("/logifleet/dashboard/data", {});
        console.log("📊 Données du dashboard :", data);

        // TODO: mettre à jour les graphiques Chart.js avec `data`
    }
}
ParcDashboard.template = "logifleet.dashboard_template";

// Enregistrer l’action client
registry.category("actions").add("parc_dashboard", ParcDashboard);
