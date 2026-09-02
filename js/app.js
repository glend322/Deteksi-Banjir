/**
 * SafeRoute - Application Logic
 * Integrasi Leaflet Map, Routing, Deteksi Banjir Semarang, dan Crowdsourcing
 */

class SafeRouteApp {
    constructor() {
        this.map = null;
        this.markersLayer = null;
        this.polygonsLayer = null;
        this.routesLayer = null;
        this.currentFilter = "all";
        this.selectedPoint = null;
        this.activeRouteId = "route-safe";
        this.activePolyline = null;
        this.userLocation = [-6.995, 110.425]; // Semarang center / user current location

        this.init();
    }

    init() {
        // Tunggu DOM siap
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", () => this.bootstrap());
        } else {
            this.bootstrap();
        }
    }

    bootstrap() {
        this.initMap();
        this.renderPolygons();
        this.renderFloodMarkers();
        this.renderInitialDetailDrawer();
        this.bindEvents();
        this.bindModals();
        this.updateTimeFreshness();
    }

    /* ==========================================================================
       Map Initialization (Leaflet)
       ========================================================================== */
    initMap() {
        const mapContainer = document.getElementById("map");
        if (!mapContainer) return;

        // Inisialisasi Map Leaflet Kota Semarang
        this.map = L.map("map", {
            center: [-6.9680, 110.4350],
            zoom: 13,
            zoomControl: false // Kita gunakan custom floating buttons
        });

        // Tile layer CartoDB Positron untuk tampilan modern, bersih, dan kontras tinggi seperti di mockup
        L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
            attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; OpenStreetMap',
            subdomains: "abcd",
            maxZoom: 19
        }).addTo(this.map);

        // Layer groups
        this.polygonsLayer = L.layerGroup().addTo(this.map);
        this.markersLayer = L.layerGroup().addTo(this.map);
        this.routesLayer = L.layerGroup().addTo(this.map);

        // Render User Location Pin (pulsing blue dot)
        this.renderUserLocationMarker();
    }

    renderUserLocationMarker() {
        const userIcon = L.divIcon({
            className: "custom-user-marker",
            html: `
                <div style="position: relative; width: 22px; height: 22px;">
                    <div style="position: absolute; inset: 0; background: #2563EB; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 10px rgba(37,99,235,0.8);"></div>
                    <div style="position: absolute; inset: -6px; background: rgba(37,99,235,0.3); border-radius: 50%; animation: pulse 2s infinite;"></div>
                </div>
            `,
            iconSize: [22, 22],
            iconAnchor: [11, 11]
        });

        L.marker(this.userLocation, { icon: userIcon })
            .addTo(this.map)
            .bindTooltip("Lokasi Anda Saat Ini", { permanent: false, direction: "top" });
    }

    /* ==========================================================================
       Render Poligon Banjir (Fill Biru + Outline Merah sesuai PRD 5 & 6.2)
       ========================================================================== */
    renderPolygons() {
        if (!this.polygonsLayer) return;
        this.polygonsLayer.clearLayers();

        SAFEROUTE_DATA.floodPolygons.forEach(poly => {
            const polygon = L.polygon(poly.coordinates, {
                color: poly.borderColor, // Outline merah / oranye
                weight: poly.borderWeight,
                fillColor: poly.fillColor, // Fill biru genangan air
                fillOpacity: poly.fillOpacity,
                dashArray: poly.status === "watch" ? "4, 6" : null
            });

            polygon.on("click", () => {
                // Cari titik terkait (misal Kaligawe)
                const point = SAFEROUTE_DATA.floodPoints.find(p => p.status === poly.status) || SAFEROUTE_DATA.floodPoints[0];
                this.openDetailDrawer(point);
            });

            polygon.bindTooltip(`<b>${poly.name}</b><br>Batas Area Terdampak`, { sticky: true });
            this.polygonsLayer.addLayer(polygon);
        });
    }

    /* ==========================================================================
       Render Marker Titik Pantau Banjir
       ========================================================================== */
    renderFloodMarkers() {
        if (!this.markersLayer) return;
        this.markersLayer.clearLayers();

        const filteredPoints = SAFEROUTE_DATA.floodPoints.filter(point => {
            if (this.currentFilter === "all") return true;
            return point.status === this.currentFilter;
        });

        filteredPoints.forEach(point => {
            let color = "#10B981";
            let iconText = "✓";
            if (point.status === "impassable") { color = "#EF4444"; iconText = "✕"; }
            else if (point.status === "flooded") { color = "#F97316"; iconText = "≈"; }
            else if (point.status === "watch") { color = "#F59E0B"; iconText = "!"; }

            const customMarker = L.divIcon({
                className: "custom-flood-pin",
                html: `
                    <div style="background: ${color}; width: 34px; height: 34px; border-radius: 50% 50% 50% 4px; transform: rotate(-45deg); display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 10px rgba(0,0,0,0.25); border: 2.5px solid white;">
                        <span style="transform: rotate(45deg); color: white; font-weight: 800; font-size: 14px;">${iconText}</span>
                    </div>
                `,
                iconSize: [34, 34],
                iconAnchor: [17, 34],
                popupAnchor: [0, -32]
            });

            const marker = L.marker([point.lat, point.lng], { icon: customMarker });

            marker.on("click", () => {
                this.openDetailDrawer(point);
            });

            marker.bindTooltip(`
                <div style="padding: 2px;">
                    <div style="font-weight: 700; color: #0F172A;">${point.name}</div>
                    <div style="font-size: 11px; color: ${color}; font-weight: 600;">${point.statusLabel} • ${point.depth > 0 ? point.depth + ' cm' : 'Bebas Genangan'}</div>
                </div>
            `, { direction: "top", offset: [0, -28] });

            this.markersLayer.addLayer(marker);
        });
    }

    /* ==========================================================================
       Detail Lokasi Drawer (Panel Kanan Desktop / Bottom Sheet Mobile)
       ========================================================================== */
    renderInitialDetailDrawer() {
        // Tampilkan default Jl. Kaligawe Raya sesuai mockup ChatGPT
        const defaultPoint = SAFEROUTE_DATA.floodPoints.find(p => p.id === "loc-kaligawe") || SAFEROUTE_DATA.floodPoints[0];
        this.openDetailDrawer(defaultPoint);
    }

    openDetailDrawer(point) {
        this.selectedPoint = point;
        const drawer = document.getElementById("detailDrawer");
        if (!drawer) return;

        // Badge class & color
        let badgeClass = "danger";
        if (point.status === "watch") badgeClass = "watch";
        else if (point.status === "flooded") badgeClass = "flooded";
        else if (point.status === "safe") badgeClass = "safe";

        // Update DOM drawer
        document.getElementById("drawerStatusBadge").className = `status-pill-badge ${badgeClass}`;
        document.getElementById("drawerStatusBadge").innerHTML = `
            <span class="pill-indicator ${point.status}"></span>
            <span>${point.statusLabel}</span>
        `;
        document.getElementById("drawerTitle").textContent = point.name;
        document.getElementById("drawerSubtitle").textContent = point.area;
        document.getElementById("drawerDepth").textContent = point.depth > 0 ? `${point.depth} cm` : "0 cm (Aman)";
        document.getElementById("drawerStatus").textContent = point.statusLabel;
        document.getElementById("drawerUpdated").textContent = point.updatedAt;
        document.getElementById("drawerSource").textContent = point.source;
        document.getElementById("drawerRecommendation").textContent = point.recommendation;

        const imgElem = document.getElementById("drawerCctvImage");
        if (imgElem && point.image) {
            imgElem.src = point.image;
        }

        // Buka drawer
        drawer.classList.add("open");

        // Pan map sedikit ke titik tersebut
        if (this.map) {
            this.map.panTo([point.lat, point.lng], { animate: true, duration: 0.8 });
        }
    }

    closeDetailDrawer() {
        const drawer = document.getElementById("detailDrawer");
        if (drawer) drawer.classList.remove("open");
    }

    /* ==========================================================================
       Rekomendasi Rute Aman (Mockup Layar 3 & PRD 5.3)
       ========================================================================== */
    renderRoutesOnMap(selectedRouteId = "route-safe") {
        if (!this.routesLayer) return;
        this.routesLayer.clearLayers();

        this.activeRouteId = selectedRouteId;

        // Draw all routes (selected highlighted, others dimmed)
        SAFEROUTE_DATA.routes.options.forEach(route => {
            const isSelected = route.id === selectedRouteId;
            const polyline = L.polyline(route.path, {
                color: route.color,
                weight: isSelected ? 6 : 3.5,
                opacity: isSelected ? 0.95 : 0.4,
                dashArray: isSelected ? null : "6, 8"
            });

            polyline.on("click", () => {
                this.selectRoute(route.id);
            });

            this.routesLayer.addLayer(polyline);

            if (isSelected) {
                this.map.fitBounds(polyline.getBounds(), { padding: [60, 60] });
            }
        });
    }

    selectRoute(routeId) {
        this.activeRouteId = routeId;

        // Update UI selector cards
        document.querySelectorAll(".route-card").forEach(card => {
            card.classList.toggle("selected", card.dataset.routeId === routeId);
        });

        this.renderRoutesOnMap(routeId);
    }

    /* ==========================================================================
       Event Handlers & Interactivity
       ========================================================================== */
    bindEvents() {
        // Filter Pills
        const pills = document.querySelectorAll(".pill-btn");
        pills.forEach(pill => {
            pill.addEventListener("click", (e) => {
                pills.forEach(p => p.classList.remove("active"));
                pill.classList.add("active");
                this.currentFilter = pill.dataset.filter;
                this.renderFloodMarkers();
            });
        });

        // Close Drawer Button
        const closeBtn = document.getElementById("btnCloseDrawer");
        if (closeBtn) {
            closeBtn.addEventListener("click", () => this.closeDetailDrawer());
        }

        // Lihat Rute Alternatif Button in Drawer
        const btnViewRoute = document.getElementById("btnViewRoute");
        if (btnViewRoute) {
            btnViewRoute.addEventListener("click", () => {
                this.closeDetailDrawer();
                this.openModal("modalRoute");
                this.renderRoutesOnMap(this.activeRouteId);
            });
        }

        // Map controls (Zoom +/- & GPS)
        const btnZoomIn = document.getElementById("btnZoomIn");
        const btnZoomOut = document.getElementById("btnZoomOut");
        const btnRecenter = document.getElementById("btnRecenter");

        if (btnZoomIn) btnZoomIn.addEventListener("click", () => this.map.zoomIn());
        if (btnZoomOut) btnZoomOut.addEventListener("click", () => this.map.zoomOut());
        if (btnRecenter) {
            btnRecenter.addEventListener("click", () => {
                this.map.setView(this.userLocation, 14, { animate: true });
                this.showToast("Lokasi Anda dipusatkan pada peta.");
            });
        }

        // Splash screen dismissal
        const btnSplashStart = document.getElementById("btnSplashStart");
        const splashOverlay = document.getElementById("splashOverlay");
        if (btnSplashStart && splashOverlay) {
            btnSplashStart.addEventListener("click", () => {
                splashOverlay.classList.add("hidden");
            });
        }

        // Device Frame Switcher (Desktop Preview Toggle)
        const btnToggleDevice = document.getElementById("btnToggleDevice");
        const appContainer = document.getElementById("appContainer");
        if (btnToggleDevice && appContainer) {
            btnToggleDevice.addEventListener("click", () => {
                const isMobileFrame = appContainer.classList.toggle("mobile-frame-mode");
                btnToggleDevice.innerHTML = isMobileFrame
                    ? `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="20" height="14" x="2" y="3" rx="2"/><line x1="8" x2="16" y1="21" y2="21"/><line x1="12" x2="12" y1="17" y2="21"/></svg> Kembali ke Desktop`
                    : `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="14" height="20" x="5" y="2" rx="2"/><path d="M12 18h.01"/></svg> Tampilan Mobile`;
                setTimeout(() => this.map.invalidateSize(), 300);
            });
        }
    }

    /* ==========================================================================
       Modals & Secondary Views Management
       ========================================================================== */
    bindModals() {
        // Desktop sidebar nav links
        const navLinks = document.querySelectorAll(".sidebar-nav .nav-item, .mobile-nav-link");
        navLinks.forEach(link => {
            link.addEventListener("click", (e) => {
                e.preventDefault();
                const targetView = link.dataset.view;

                // Mark active
                navLinks.forEach(l => l.classList.remove("active"));
                link.classList.add("active");

                if (targetView === "peta") {
                    this.closeAllModals();
                } else if (targetView === "rute") {
                    this.openModal("modalRoute");
                    this.renderRoutesOnMap(this.activeRouteId);
                } else if (targetView === "peringatan") {
                    this.openModal("modalAlerts");
                } else if (targetView === "laporan") {
                    this.openModal("modalReport");
                } else if (targetView === "riwayat") {
                    this.openModal("modalHistory");
                } else if (targetView === "edukasi") {
                    this.openModal("modalEducation");
                } else if (targetView === "profil") {
                    this.openModal("modalProfile");
                }
            });
        });

        // "+ Laporkan Banjir" Sidebar button
        const btnSidebarReport = document.getElementById("btnSidebarReport");
        if (btnSidebarReport) {
            btnSidebarReport.addEventListener("click", () => this.openModal("modalReport"));
        }

        // Close modal buttons
        document.querySelectorAll(".btn-close-modal").forEach(btn => {
            btn.addEventListener("click", () => this.closeAllModals());
        });

        // Close on overlay click
        document.querySelectorAll(".modal-overlay").forEach(overlay => {
            overlay.addEventListener("click", (e) => {
                if (e.target === overlay) this.closeAllModals();
            });
        });

        // Route card clicks
        document.querySelectorAll(".route-card").forEach(card => {
            card.addEventListener("click", () => {
                this.selectRoute(card.dataset.routeId);
            });
        });

        // "Mulai Navigasi" button
        const btnStartNavigation = document.getElementById("btnStartNavigation");
        if (btnStartNavigation) {
            btnStartNavigation.addEventListener("click", () => {
                this.closeAllModals();
                this.showToast("Navigasi aktif! Mengarahkan via Rute Teraman...");
            });
        }

        // Laporan Form interactivity
        this.bindReportForm();
    }

    bindReportForm() {
        const depthButtons = document.querySelectorAll(".option-pill-btn[data-depth]");
        depthButtons.forEach(btn => {
            btn.addEventListener("click", () => {
                depthButtons.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
            });
        });

        const conditionButtons = document.querySelectorAll(".option-pill-btn[data-condition]");
        conditionButtons.forEach(btn => {
            btn.addEventListener("click", () => {
                conditionButtons.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
            });
        });

        // Tombol Gunakan Lokasi Saya
        const btnUseMyLocation = document.getElementById("btnUseMyLocation");
        if (btnUseMyLocation) {
            btnUseMyLocation.addEventListener("click", () => {
                document.getElementById("reportLocationInput").value = "Jl. Madukoro Raya, Semarang Barat";
                this.showToast("Lokasi GPS Anda berhasil dimasukkan.");
            });
        }

        // Form Submit
        const btnSubmitReport = document.getElementById("btnSubmitReport");
        if (btnSubmitReport) {
            btnSubmitReport.addEventListener("click", () => {
                const loc = document.getElementById("reportLocationInput").value || "Jl. Madukoro Raya";
                const activeDepth = document.querySelector(".option-pill-btn[data-depth].active");
                const depthText = activeDepth ? activeDepth.textContent : "40-70 cm";
                const activeCondition = document.querySelector(".option-pill-btn[data-condition].active");
                const condition = activeCondition ? activeCondition.textContent : "Tergenang";

                // Tambahkan titik baru ke peta
                const newPoint = {
                    id: "loc-user-" + Date.now(),
                    name: loc,
                    area: "Semarang (Laporan Komunitas)",
                    lat: -6.975 + (Math.random() - 0.5) * 0.02,
                    lng: 110.420 + (Math.random() - 0.5) * 0.02,
                    status: condition === "Tidak Dapat Dilalui" ? "impassable" : "flooded",
                    statusLabel: condition,
                    depth: 45,
                    updatedAt: "Baru saja",
                    source: "Laporan Warga (Terverifikasi AI)",
                    confidence: 94,
                    image: "assets/cctv_kaligawe.jpg",
                    recommendation: "Hindari genangan, pantau perkembangan rute."
                };

                SAFEROUTE_DATA.floodPoints.unshift(newPoint);
                this.renderFloodMarkers();
                this.closeAllModals();
                this.showToast(`Laporan Anda untuk ${loc} berhasil dikirim & terverifikasi AI!`);
                this.openDetailDrawer(newPoint);
            });
        }
    }

    openModal(modalId) {
        this.closeAllModals();
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.add("open");
    }

    closeAllModals() {
        document.querySelectorAll(".modal-overlay").forEach(m => m.classList.remove("open"));
    }

    showToast(message) {
        let toast = document.getElementById("appToast");
        if (!toast) {
            toast = document.createElement("div");
            toast.id = "appToast";
            toast.style.cssText = `
                position: fixed;
                bottom: 84px;
                left: 50%;
                transform: translateX(-50%) translateY(30px);
                background: #0F172A;
                color: #FFFFFF;
                padding: 12px 24px;
                border-radius: 9999px;
                font-size: 13px;
                font-weight: 700;
                box-shadow: 0 10px 25px rgba(0,0,0,0.3);
                z-index: 3000;
                opacity: 0;
                transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
                pointer-events: none;
                text-align: center;
                max-width: 90%;
            `;
            document.body.appendChild(toast);
        }

        toast.textContent = message;
        toast.style.opacity = "1";
        toast.style.transform = "translateX(-50%) translateY(0)";

        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateX(-50%) translateY(30px)";
        }, 3500);
    }

    updateTimeFreshness() {
        // Update freshness counter every minute
        setInterval(() => {
            const statusBox = document.querySelector(".sidebar-status-box span");
            if (statusBox) {
                statusBox.textContent = `Data Terakhir Diperbarui ${Math.floor(Math.random() * 5 + 5)} menit lalu`;
            }
        }, 60000);
    }
}

// Start Application
window.app = new SafeRouteApp();
