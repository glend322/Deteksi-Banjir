/**
 * SafeRoute - Alerts Module
 */

class AlertsModule {
    constructor(app) {
        this.app = app;
    }

    init() {
        // Tab filter for alerts modal
        const tabs = document.querySelectorAll("#modalAlerts .tab-btn");
        tabs.forEach(tab => {
            tab.addEventListener("click", () => {
                tabs.forEach(t => t.classList.remove("active"));
                tab.classList.add("active");
            });
        });
    }
}

if (typeof window !== "undefined") {
    window.AlertsModule = AlertsModule;
}
