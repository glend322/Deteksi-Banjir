/**
 * SafeRoute - Detail Location Drawer Module
 */

class DrawerModule {
    constructor(app) {
        this.app = app;
        this.selectedPoint = null;
    }

    init() {
        const closeBtn = document.getElementById("btnCloseDrawer");
        if (closeBtn) {
            closeBtn.addEventListener("click", () => this.close());
        }

        const btnViewRoute = document.getElementById("btnViewRoute");
        if (btnViewRoute) {
            btnViewRoute.addEventListener("click", () => {
                this.close();
                this.app.openModal("modalRoute");
                if (this.app.routesModule) {
                    this.app.routesModule.renderRoutesOnMap();
                }
            });
        }

        // Tampilkan default Kaligawe jika ada
        const defaultPoint = (SAFEROUTE_DATA.floodPoints || []).find(p => p.id === "loc-kaligawe") || (SAFEROUTE_DATA.floodPoints || [])[0];
        if (defaultPoint) {
            this.open(defaultPoint, false);
        }
    }

    open(point, panMap = true) {
        this.selectedPoint = point;
        const drawer = document.getElementById("detailDrawer");
        if (!drawer) return;

        let badgeClass = "danger";
        if (point.status === "watch") badgeClass = "watch";
        else if (point.status === "flooded") badgeClass = "flooded";
        else if (point.status === "safe") badgeClass = "safe";

        const badgeElem = document.getElementById("drawerStatusBadge");
        if (badgeElem) {
            badgeElem.className = `status-pill-badge ${badgeClass}`;
            badgeElem.innerHTML = `
                <span class="pill-indicator ${point.status}"></span>
                <span>${point.statusLabel}</span>
            `;
        }

        const titleElem = document.getElementById("drawerTitle");
        if (titleElem) titleElem.textContent = point.name;

        const subElem = document.getElementById("drawerSubtitle");
        if (subElem) subElem.textContent = point.area;

        const depthElem = document.getElementById("drawerDepth");
        if (depthElem) depthElem.textContent = point.depth > 0 ? `${point.depth} cm` : "0 cm (Aman)";

        const statusElem = document.getElementById("drawerStatus");
        if (statusElem) statusElem.textContent = point.statusLabel;

        const updatedElem = document.getElementById("drawerUpdated");
        if (updatedElem) updatedElem.textContent = point.updatedAt;

        const sourceElem = document.getElementById("drawerSource");
        if (sourceElem) sourceElem.textContent = point.source;

        const recElem = document.getElementById("drawerRecommendation");
        if (recElem) recElem.textContent = point.recommendation;

        const imgElem = document.getElementById("drawerCctvImage");
        if (imgElem && point.image) {
            imgElem.src = point.image;
        }

        drawer.classList.add("open");

        if (panMap && this.app.mapModule && this.app.mapModule.map) {
            this.app.mapModule.map.panTo([point.lat, point.lng], { animate: true, duration: 0.8 });
        }
    }

    close() {
        const drawer = document.getElementById("detailDrawer");
        if (drawer) drawer.classList.remove("open");
    }
}

if (typeof window !== "undefined") {
    window.DrawerModule = DrawerModule;
}
