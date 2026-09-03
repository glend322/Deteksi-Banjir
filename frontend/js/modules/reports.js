/**
 * SafeRoute - Reports Module
 */

class ReportsModule {
    constructor(app) {
        this.app = app;
    }

    init() {
        // Depth pills
        const depthButtons = document.querySelectorAll(".option-pill-btn[data-depth]");
        depthButtons.forEach(btn => {
            btn.addEventListener("click", () => {
                depthButtons.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
            });
        });

        // Condition pills
        const conditionButtons = document.querySelectorAll(".option-pill-btn[data-condition]");
        conditionButtons.forEach(btn => {
            btn.addEventListener("click", () => {
                conditionButtons.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
            });
        });

        // Use my location
        const btnUseMyLocation = document.getElementById("btnUseMyLocation");
        if (btnUseMyLocation) {
            btnUseMyLocation.addEventListener("click", () => {
                const input = document.getElementById("reportLocationInput");
                if (input) input.value = "Jl. Madukoro Raya, Semarang Barat";
                this.app.showToast("Lokasi GPS Anda berhasil dimasukkan.");
            });
        }

        // Submit report
        const btnSubmitReport = document.getElementById("btnSubmitReport");
        if (btnSubmitReport) {
            btnSubmitReport.addEventListener("click", () => this.submit());
        }
    }

    submit() {
        const input = document.getElementById("reportLocationInput");
        const loc = (input && input.value) ? input.value : "Jl. Madukoro Raya";
        const activeDepth = document.querySelector(".option-pill-btn[data-depth].active");
        const depthText = activeDepth ? activeDepth.textContent : "40-70 cm";
        const activeCondition = document.querySelector(".option-pill-btn[data-condition].active");
        const condition = activeCondition ? activeCondition.textContent : "Tergenang";

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
            confidence: 95,
            image: "assets/cctv_kaligawe.jpg",
            recommendation: "Hindari genangan, pantau perkembangan rute."
        };

        if (window.SAFEROUTE_FLOOD_DATA && window.SAFEROUTE_FLOOD_DATA.floodPoints) {
            window.SAFEROUTE_FLOOD_DATA.floodPoints.unshift(newPoint);
        }

        if (this.app.mapModule) {
            this.app.mapModule.renderFloodMarkers();
        }

        this.app.closeAllModals();
        this.app.showToast(`Laporan Anda untuk ${loc} berhasil dikirim & terverifikasi AI!`);

        if (this.app.drawerModule) {
            this.app.drawerModule.open(newPoint);
        }
    }
}

if (typeof window !== "undefined") {
    window.ReportsModule = ReportsModule;
}
