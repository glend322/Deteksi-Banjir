/**
 * SafeRoute - Component Loader Module
 * Memuat berkas komponen HTML modular secara terpisah per fungsi
 * Mendukung pemuatan dinamis via fetch (HTTP/S) dan fallback registry (file://)
 */

class ComponentLoader {
    constructor() {
        this.slotMap = {
            "component-splash": "components/splash.html",
            "component-sidebar": "components/sidebar.html",
            "component-topbar": "components/topbar.html",
            "component-beranda": "components/beranda.html",
            "component-map": "components/map.html",
            "component-drawer": "components/drawer.html",
            "component-mobile-nav": "components/mobile-nav.html",
            "component-modal-route": "components/modal-route.html",
            "component-modal-alerts": "components/modal-alerts.html",
            "component-modal-report": "components/modal-report.html",
            "component-modal-history": "components/modal-history.html",
            "component-modal-education": "components/modal-education.html",
            "component-modal-weather": "components/modal-weather.html",
            "component-modal-profile": "components/modal-profile.html"
        };
    }

    async loadAll() {
        const canFetch = window.location.protocol.startsWith("http");

        if (canFetch) {
            try {
                const entries = Object.entries(this.slotMap);
                await Promise.all(entries.map(async ([slotId, filePath]) => {
                    const el = document.getElementById(slotId);
                    if (!el) return;
                    const res = await fetch(filePath);
                    if (!res.ok) throw new Error(`HTTP ${res.status} for ${filePath}`);
                    el.outerHTML = await res.text();
                }));
                return true;
            } catch (err) {
                console.warn("Fetch component encountered issue, loading from registry:", err);
                this.loadFromRegistry();
                return false;
            }
        } else {
            this.loadFromRegistry();
            return true;
        }
    }

    loadFromRegistry() {
        if (!window.COMPONENTS_REGISTRY) return;
        for (const [slotId, filePath] of Object.entries(this.slotMap)) {
            const el = document.getElementById(slotId);
            if (el && window.COMPONENTS_REGISTRY[filePath]) {
                el.outerHTML = window.COMPONENTS_REGISTRY[filePath];
            }
        }
    }
}

if (typeof window !== "undefined") {
    window.ComponentLoader = ComponentLoader;
}
