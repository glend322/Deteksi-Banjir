/**
 * SafeRoute - Routes Module
 */

class RoutesModule {
    constructor(app) {
        this.app = app;
        this.activeRouteId = "route-safe";
    }

    init() {
        // Route cards selector
        document.querySelectorAll(".route-card").forEach(card => {
            card.addEventListener("click", () => {
                this.selectRoute(card.dataset.routeId);
            });
        });

        // Start navigation button
        const btnStartNav = document.getElementById("btnStartNavigation");
        if (btnStartNav) {
            btnStartNav.addEventListener("click", () => {
                this.app.closeAllModals();
                this.app.switchView("peta");
                this.app.showToast("Navigasi aktif! Mengarahkan via Rute Teraman...");
            });
        }
    }

    renderRoutesOnMap(selectedRouteId = null) {
        if (selectedRouteId) this.activeRouteId = selectedRouteId;
        const mapMod = this.app.mapModule;
        if (!mapMod || !mapMod.routesLayer || !mapMod.map) return;

        mapMod.routesLayer.clearLayers();

        const routes = (SAFEROUTE_DATA.routes && SAFEROUTE_DATA.routes.options) || [];
        routes.forEach(route => {
            const isSelected = route.id === this.activeRouteId;
            const polyline = L.polyline(route.path, {
                color: route.color,
                weight: isSelected ? 6 : 3.5,
                opacity: isSelected ? 0.95 : 0.4,
                dashArray: isSelected ? null : "6, 8"
            });

            polyline.on("click", () => {
                this.selectRoute(route.id);
            });

            mapMod.routesLayer.addLayer(polyline);

            if (isSelected) {
                mapMod.map.fitBounds(polyline.getBounds(), { padding: [60, 60] });
            }
        });
    }

    selectRoute(routeId) {
        this.activeRouteId = routeId;

        document.querySelectorAll(".route-card").forEach(card => {
            card.classList.toggle("selected", card.dataset.routeId === routeId);
        });

        this.renderRoutesOnMap(routeId);
    }
}

if (typeof window !== "undefined") {
    window.RoutesModule = RoutesModule;
}
