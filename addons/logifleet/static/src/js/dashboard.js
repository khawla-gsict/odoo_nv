/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class LogifleetDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.data = {};

        onWillStart(async () => {
            this.data = await this.orm.call(
                "logifleet.dashboard",
                "get_kpis",
                []
            );
        });
    }
}

LogifleetDashboard.template = "logifleet.Dashboard";
registry.category("actions").add("logifleet_dashboard", LogifleetDashboard);
