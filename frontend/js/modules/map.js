/**
 * SafeRoute - Map Module
 * Integrasi Leaflet Map, Tile Layer, Marker Banjir, Poligon Risiko, dan User GPS Marker
 */

class MapModule {
    constructor(app) {
        this.app = app;
        this.map = null;
        this.markersLayer = null;
        this.polygonsLayer = null;
        this.routesLayer = null;
        this.currentFilter = "all";
        this.userLocation = [-6.995, 110.425]; // Semarang center
    }

    init() {
        this.initMap();
        this.renderPolygons();
        this.renderFloodMarkers();
        this.bindEvents();
    }

    initMap() {
        const mapContainer = document.getElementById("map");
        if (!mapContainer || this.map) return;

        this.map = L.map("map", {
            center: [-6.9680, 110.4350],
            zoom: 13,
            zoomControl: false
        });

        L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
            attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; OpenStreetMap',
            subdomains: "abcd",
            maxZoom: 19
        }).addTo(this.map);

        this.polygonsLayer = L.layerGroup().addTo(this.map);
        this.markersLayer = L.layerGroup().addTo(this.map);
        this.routesLayer = L.layerGroup().addTo(this.map);

        this.renderUserLocationMarker();
    }

    renderUserLocationMarker() {
        if (!this.map) return;
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
            .bindTooltip("Lokasi Anda Saat Ini (Semarang)", { permanent: false, direction: "top" });
    }

    renderPolygons() {
        if (!this.polygonsLayer) return;
        this.polygonsLayer.clearLayers();

        const polygons = SAFEROUTE_DATA.floodPolygons || [];
        polygons.forEach(poly => {
            const polygon = L.polygon(poly.coordinates, {
                color: poly.borderColor,
                weight: poly.borderWeight,
                fillColor: poly.fillColor,
                fillOpacity: poly.fillOpacity,
                dashArray: poly.status === "watch" ? "4, 6" : null
            });

            polygon.on("click", () => {
                const point = (SAFEROUTE_DATA.floodPoints || []).find(p => p.status === poly.status) || (SAFEROUTE_DATA.floodPoints || [])[0];
                if (point && this.app.drawerModule) {
                    this.app.drawerModule.open(point);
                }
            });

            polygon.bindTooltip(`<b>${poly.name}</b><br>Batas Area Terdampak`, { sticky: true });
            this.polygonsLayer.addLayer(polygon);
        });
    }

    renderFloodMarkers() {
        if (!this.markersLayer) return;
        this.markersLayer.clearLayers();

        const points = (SAFEROUTE_DATA.floodPoints || []).filter(p => {
            if (this.currentFilter === "all") return true;
            return p.status === this.currentFilter;
        });

        points.forEach(point => {
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
                if (this.app.drawerModule) {
                    this.app.drawerModule.open(point);
                }
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

    bindEvents() {
        // Filter Pills
        const pills = document.querySelectorAll(".pill-btn");
        pills.forEach(pill => {
            pill.addEventListener("click", () => {
                pills.forEach(p => p.classList.remove("active"));
                pill.classList.add("active");
                this.currentFilter = pill.dataset.filter;
                this.renderFloodMarkers();
            });
        });

        // Zoom & GPS controls
        const btnZoomIn = document.getElementById("btnZoomIn");
        const btnZoomOut = document.getElementById("btnZoomOut");
        const btnRecenter = document.getElementById("btnRecenter");

        if (btnZoomIn) btnZoomIn.addEventListener("click", () => this.map && this.map.zoomIn());
        if (btnZoomOut) btnZoomOut.addEventListener("click", () => this.map && this.map.zoomOut());
        if (btnRecenter) {
            btnRecenter.addEventListener("click", () => {
                if (this.map) {
                    this.map.setView(this.userLocation, 14, { animate: true });
                    this.app.showToast("Lokasi GPS Anda dipusatkan pada peta.");
                }
            });
        }
    }

    invalidateSize() {
        if (this.map) {
            setTimeout(() => this.map.invalidateSize(), 200);
        }
    }
}

if (typeof window !== "undefined") {
    window.MapModule = MapModule;
}
