/**
 * SafeRoute - Main Application Coordinator
 * Mengatur orkestrasikan modul: Beranda, Peta, Navigasi Rute, Modal, dan Komunikasi Antarmuka
 */

class SafeRouteApp {
    constructor() {
        this.currentView = "beranda"; // Default view: Beranda (Dashboard Utama)
        this.berandaModule = null;
        this.mapModule = null;
        this.drawerModule = null;
        this.routesModule = null;
        this.alertsModule = null;
        this.reportsModule = null;
        this.historyModule = null;
        this.contactsModule = null;
        this.educationModule = null;
        this.profileModule = null;
        this.weatherModule = null;

        this.init();
    }

    init() {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", () => this.bootstrap());
        } else {
            this.bootstrap();
        }
    }

    async bootstrap() {
        // 1. Muat seluruh komponen HTML modular per fungsi
        this.componentLoader = new ComponentLoader();
        await this.componentLoader.loadAll();

        // 2. Inisialisasi sub-modul
        this.mapModule = new MapModule(this);
        this.mapModule.init();

        this.drawerModule = new DrawerModule(this);
        this.drawerModule.init();

        this.berandaModule = new BerandaModule(this);
        window.berandaModule = this.berandaModule;
        this.berandaModule.init();

        this.routesModule = new RoutesModule(this);
        this.routesModule.init();

        this.alertsModule = new AlertsModule(this);
        this.alertsModule.init();

        this.reportsModule = new ReportsModule(this);
        this.reportsModule.init();

        this.historyModule = new HistoryModule(this);
        this.historyModule.init();

        this.contactsModule = new ContactsModule(this);
        this.contactsModule.init();

        this.educationModule = new EducationModule(this);
        this.educationModule.init();

        this.profileModule = new ProfileModule(this);
        this.profileModule.init();

        this.weatherModule = new WeatherModule(this);
        this.weatherModule.init();

        this.bindGlobalNavigation();
        this.bindShellEvents();
        this.updateTimeFreshness();

        // Tampilkan view awal (Beranda)
        this.switchView("beranda");
    }

    /* ==========================================================================
       View Routing (Beranda vs Peta)
       ========================================================================== */
    switchView(viewName) {
        this.currentView = viewName;
        const berandaPane = document.getElementById("berandaView");
        const mapPane = document.getElementById("mapView");

        if (viewName === "beranda") {
            if (berandaPane) berandaPane.classList.add("active");
            if (mapPane) mapPane.classList.remove("active");
        } else if (viewName === "peta") {
            if (berandaPane) berandaPane.classList.remove("active");
            if (mapPane) mapPane.classList.add("active");
            if (this.mapModule) {
                this.mapModule.invalidateSize();
            }
        }

        // Update active class pada navigasi sidebar dan mobile bottom nav
        const navLinks = document.querySelectorAll(".sidebar-nav .nav-item, .mobile-nav-link");
        navLinks.forEach(link => {
            const isMatch = link.dataset.view === viewName;
            link.classList.toggle("active", isMatch);
        });

        this.closeAllModals();
    }

    /* ==========================================================================
       Global Navigation & Action Buttons
       ========================================================================== */
    bindGlobalNavigation() {
        const navLinks = document.querySelectorAll(".sidebar-nav .nav-item, .mobile-nav-link");
        navLinks.forEach(link => {
            link.addEventListener("click", (e) => {
                e.preventDefault();
                const targetView = link.dataset.view;

                if (targetView === "beranda") {
                    this.switchView("beranda");
                } else if (targetView === "peta") {
                    this.switchView("peta");
                } else if (targetView === "rute") {
                    this.switchView("peta");
                    this.openModal("modalRoute");
                    if (this.routesModule) {
                        this.routesModule.renderRoutesOnMap();
                    }
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

        // Close on modal overlay click
        document.querySelectorAll(".modal-overlay").forEach(overlay => {
            overlay.addEventListener("click", (e) => {
                if (e.target === overlay) this.closeAllModals();
            });
        });
    }

    /* ==========================================================================
       Shell Controls (Splash, Device Frame, Search)
       ========================================================================== */
    bindShellEvents() {
        // Splash Screen Dismissal
        const btnSplashStart = document.getElementById("btnSplashStart");
        const splashOverlay = document.getElementById("splashOverlay");
        if (btnSplashStart && splashOverlay) {
            btnSplashStart.addEventListener("click", () => {
                splashOverlay.classList.add("hidden");
            });
        }

        // Toggle Mobile / Desktop View
        const btnToggleDevice = document.getElementById("btnToggleDevice");
        const appContainer = document.getElementById("appContainer");
        if (btnToggleDevice && appContainer) {
            btnToggleDevice.addEventListener("click", () => {
                const isMobileFrame = appContainer.classList.toggle("mobile-frame-mode");
                btnToggleDevice.innerHTML = isMobileFrame
                    ? `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="20" height="14" x="2" y="3" rx="2"/><line x1="8" x2="16" y1="21" y2="21"/><line x1="12" x2="12" y1="17" y2="21"/></svg> Kembali ke Desktop`
                    : `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="14" height="20" x="5" y="2" rx="2"/><path d="M12 18h.01"/></svg> Tampilan Mobile`;
                if (this.mapModule) {
                    this.mapModule.invalidateSize();
                }
            });
        }
    }

    navigateToShelter(shelterName) {
        this.switchView("peta");
        const destInput = document.querySelector(".route-field:nth-child(2) input");
        if (destInput) destInput.value = shelterName;
        this.openModal("modalRoute");
        if (this.routesModule) {
            this.routesModule.renderRoutesOnMap();
        }
        this.showToast(`Rute diarahkan menuju posko: ${shelterName}`);
    }

    /* ==========================================================================
       Modals & Toast Helpers
       ========================================================================== */
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
        setInterval(() => {
            const statusBox = document.querySelector(".sidebar-status-box span");
            if (statusBox) {
                statusBox.textContent = `Data Terakhir Diperbarui ${Math.floor(Math.random() * 5 + 5)} menit lalu`;
            }
        }, 60000);
    }
}

// Inisialisasi Aplikasi SafeRoute
window.app = new SafeRouteApp();
