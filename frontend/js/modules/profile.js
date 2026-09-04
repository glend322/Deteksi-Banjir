/**
 * SafeRoute - Profile Module
 */

class ProfileModule {
    constructor(app) {
        this.app = app;
    }

    init() {
        const vehicleSelect = document.getElementById("profileVehicleSelect");
        if (vehicleSelect) {
            vehicleSelect.addEventListener("change", (e) => {
                this.app.showToast(`Kendaraan diubah ke: ${e.target.value}. Toleransi banjir diperbarui.`);
            });
        }
    }
}

if (typeof window !== "undefined") {
    window.ProfileModule = ProfileModule;
}
