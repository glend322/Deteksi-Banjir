/**
 * SafeRoute - History Module
 */

class HistoryModule {
    constructor(app) {
        this.app = app;
    }

    init() {
        const tabs = document.querySelectorAll("#modalHistory .tab-btn");
        tabs.forEach(tab => {
            tab.addEventListener("click", () => {
                tabs.forEach(t => t.classList.remove("active"));
                tab.classList.add("active");
            });
        });
    }
}

if (typeof window !== "undefined") {
    window.HistoryModule = HistoryModule;
}
