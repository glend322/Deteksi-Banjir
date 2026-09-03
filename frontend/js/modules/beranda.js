/**
 * SafeRoute - Beranda (Home / Dashboard) Module
 * Menangani render dashboard utama, direktori kontak darurat, telemetri TMA & pompa air,
 * kapasitas posko evakuasi, cuaca BMKG, panduan siaga, dan feed warga terkini.
 */

class BerandaModule {
    constructor(app) {
        this.app = app;
        this.activeContactCategory = "all";
    }

    init() {
        this.renderHeroAlert();
        this.renderKpiStats();
        this.renderContactsSection();
        this.renderSensorsSection();
        this.renderWeatherSection();
        this.renderSheltersSection();
        this.renderGuidesSection();
        this.renderCommunityFeed();
        this.bindEvents();
    }

    /* ==========================================================================
       1. Render Hero Emergency Alert Banner
       ========================================================================== */
    renderHeroAlert() {
        const container = document.getElementById("berandaHeroWrap");
        if (!container) return;

        container.innerHTML = `
            <div class="beranda-hero">
                <div class="hero-content">
                    <div class="hero-badge-row">
                        <span class="hero-status-pill">
                            <span class="hero-status-dot"></span>
                            STATUS: SIAGA II (WASPADA ROB & HUJAN)
                        </span>
                        <span class="hero-time-tag">Diperbarui: ${SAFEROUTE_DATA.appInfo.lastUpdated || "Baru saja"}</span>
                    </div>

                    <h1 class="hero-title">Banjir Terpantau di Kawasan Genuk & Semarang Utara</h1>
                    <p class="hero-desc">
                        Curah hujan lebat di hulu bertepatan dengan puncak pasang air laut (Rob +110 cm).
                        Jl. Kaligawe Raya dan Tambakrejo saat ini <strong>tidak dapat dilalui</strong> kendaraan roda dua dan sedan.
                        Gunakan rute alternatif yang direkomendasikan sistem AI.
                    </p>

                    <div class="hero-actions">
                        <button id="btnHeroToMap" class="btn-hero-primary" type="button">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/><line x1="9" x2="9" y1="3" y2="18"/><line x1="15" x2="15" y1="6" y2="21"/></svg>
                            Pantau di Peta Interaktif
                        </button>
                        <button id="btnHeroReport" class="btn-hero-outline" type="button">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><line x1="12" x2="12" y1="5" y2="19"/><line x1="5" x2="19" y1="12" y2="12"/></svg>
                            Laporkan Kondisi Jalan
                        </button>
                        <a href="tel:112" class="hero-emergency-call-btn">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
                            Panggilan Darurat 112
                        </a>
                    </div>
                </div>

                <div class="hero-side-illustration">
                    <span style="font-size: 38px;">🌧️</span>
                    <div class="side-weather-temp">27°C</div>
                    <div class="side-weather-condition">Hujan Ringan</div>
                    <div class="side-weather-sub">Kota Semarang • BMKG</div>
                </div>
            </div>
        `;
    }

    /* ==========================================================================
       2. Render KPI Metrics Bar
       ========================================================================== */
    renderKpiStats() {
        const container = document.getElementById("berandaKpiGrid");
        if (!container) return;

        const risk = SAFEROUTE_DATA.riskSummary;
        container.innerHTML = `
            <div class="kpi-card danger">
                <div class="kpi-header">
                    <div class="kpi-icon-box danger">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                    </div>
                    <span class="kpi-badge danger">${risk.impassable ? risk.impassable.count : 2} Jalur Putus</span>
                </div>
                <div class="kpi-value">${risk.impassable ? risk.impassable.count + risk.flooded.count : 7} Titik</div>
                <div class="kpi-label">Genangan Kritis & Terendam</div>
                <div class="kpi-subtext">Kaligawe & Semarang Utara perlu dihindari</div>
            </div>

            <div class="kpi-card watch">
                <div class="kpi-header">
                    <div class="kpi-icon-box watch">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/></svg>
                    </div>
                    <span class="kpi-badge watch">Maks 60 cm</span>
                </div>
                <div class="kpi-value">60 cm</div>
                <div class="kpi-label">Kedalaman Air Tertinggi</div>
                <div class="kpi-subtext">Lokasi: Jl. Kaligawe KM 4 (CCTV PU)</div>
            </div>

            <div class="kpi-card primary">
                <div class="kpi-header">
                    <div class="kpi-icon-box primary">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
                    </div>
                    <span class="kpi-badge primary">38/42 Pompa Aktif</span>
                </div>
                <div class="kpi-value">90.5%</div>
                <div class="kpi-label">Kapasitas Pompa Beroperasi</div>
                <div class="kpi-subtext">Rumah Pompa Kaligawe & Tenggang 100%</div>
            </div>

            <div class="kpi-card safe">
                <div class="kpi-header">
                    <div class="kpi-icon-box safe">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
                    </div>
                    <span class="kpi-badge safe">4 Posko Dibuka</span>
                </div>
                <div class="kpi-value">1.850 Jiwa</div>
                <div class="kpi-label">Sisa Daya Tampung Pengungsi</div>
                <div class="kpi-subtext">Posko MAJT & BPSDM Srondol Siaga Penuh</div>
            </div>
        `;
    }

    /* ==========================================================================
       3. Render Direktori Kontak & Lembaga Darurat (FITUR UTAMA)
       ========================================================================== */
    renderContactsSection() {
        const container = document.getElementById("berandaContactsGrid");
        if (!container) return;

        const allContacts = SAFEROUTE_DATA.emergencyContacts || [];
        const filtered = this.activeContactCategory === "all"
            ? allContacts
            : allContacts.filter(c => c.category === this.activeContactCategory);

        container.innerHTML = filtered.map(item => `
            <div class="contact-card" data-contact-id="${item.id}">
                <div class="contact-top-row">
                    <div class="contact-icon-box ${item.theme}">
                        <span>${item.icon}</span>
                    </div>
                    <div class="contact-meta">
                        <div class="contact-name">${item.name}</div>
                        <div class="contact-desc">${item.desc}</div>
                    </div>
                </div>

                <div class="contact-status-row">
                    <span class="contact-uptime ${item.statusType}">
                        <span style="width: 7px; height: 7px; border-radius: 50%; background: currentColor; display: inline-block;"></span>
                        ${item.status}
                    </span>
                    <div class="contact-number-box">
                        <span>📞 ${item.formattedNumber}</span>
                    </div>
                </div>

                <div class="contact-btn-group">
                    <a href="${item.phoneUrl}" class="btn-call-now ${item.isUrgent ? 'urgent' : ''}">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
                        Panggil Sekarang
                    </a>
                    <button type="button" class="btn-copy-num" title="Salin Nomor" onclick="window.berandaModule.copyNumber('${item.number}', '${item.shortName}')">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
                    </button>
                </div>
            </div>
        `).join("");
    }

    /* ==========================================================================
       4. Render Telemetri TMA & Status Pompa (WIDGET PENDUKUNG)
       ========================================================================== */
    renderSensorsSection() {
        const container = document.getElementById("berandaSensorsList");
        if (!container) return;

        const sensors = SAFEROUTE_DATA.waterSensors || [];
        container.innerHTML = sensors.map(s => {
            const percent = Math.min(100, Math.round((s.tmaCurrent / s.tmaDanger) * 100));
            return `
                <div class="sensor-item-card">
                    <div class="sensor-top-info">
                        <div class="sensor-name">
                            <span>🌊</span>
                            ${s.name}
                            <span style="font-size: 11px; font-weight: 500; color: var(--text-muted);">(${s.location})</span>
                        </div>
                        <div class="sensor-tma-val ${s.status}">${s.tmaCurrent} cm <span style="font-size: 11px; font-weight: 600;">(${s.statusLabel})</span></div>
                    </div>
                    <div class="sensor-progress-track">
                        <div class="sensor-progress-fill ${s.status}" style="width: ${percent}%;"></div>
                    </div>
                    <div class="sensor-bottom-meta">
                        <span class="pump-active-tag">⚙️ Pompa: ${s.pumpsActive}/${s.pumpsTotal} Aktif</span>
                        <span>Tren: ${s.flowTrend}</span>
                        <span>${s.updatedAt}</span>
                    </div>
                </div>
            `;
        }).join("");
    }

    /* ==========================================================================
       5. Render BMKG Weather Timeline
       ========================================================================== */
    renderWeatherSection() {
        const container = document.getElementById("berandaWeatherInner");
        if (!container) return;

        const w = SAFEROUTE_DATA.weather || {};
        const hourly = w.forecastHourly || [];

        container.innerHTML = `
            <div class="weather-current-banner">
                <div>
                    <div style="font-size: 12px; font-weight: 700; color: #1E40AF;">Kondisi Terkini di Kota Semarang</div>
                    <div class="weather-temp-huge">${w.temp || 27}°C</div>
                    <div style="font-size: 13px; font-weight: 700; color: #1E3A8A; margin-top: 4px;">${w.condition || "Hujan Ringan"}</div>
                </div>
                <div style="text-align: right; font-size: 11px; color: #1E40AF;">
                    <div>💧 Kelembaban: <strong>${w.humidity || 86}%</strong></div>
                    <div style="margin-top: 3px;">💨 Angin: <strong>${w.windSpeed || "14 km/jam"}</strong></div>
                    <div style="margin-top: 3px;">🌧️ Curah Hujan: <strong>${w.rainfallRate || "42 mm/jam"}</strong></div>
                </div>
            </div>

            <div style="font-size: 12px; font-weight: 800; color: var(--text-primary); margin-top: 8px;">Prakiraan Per Jam (BMKG)</div>
            <div class="weather-hourly-slider">
                ${hourly.map((h, idx) => `
                    <div class="weather-hour-box ${idx === 0 ? 'now' : ''}">
                        <span class="hour-time">${h.time}</span>
                        <span style="font-size: 20px;">${h.icon || '🌧️'}</span>
                        <span class="hour-temp">${h.temp}°C</span>
                        <span class="hour-rain-tag">${h.rainProb || '50%'}</span>
                    </div>
                `).join("")}
            </div>
        `;
    }

    /* ==========================================================================
       6. Render Status Posko Evakuasi
       ========================================================================== */
    renderSheltersSection() {
        const container = document.getElementById("berandaSheltersGrid");
        if (!container) return;

        const shelters = SAFEROUTE_DATA.evacuationPoints || [];
        container.innerHTML = shelters.map(item => `
            <div class="shelter-card">
                <div class="shelter-header">
                    <div class="shelter-title">${item.name}</div>
                    <span class="shelter-status-tag ${item.status === 'crowded' ? 'crowded' : 'ready'}">${item.statusLabel || item.status}</span>
                </div>
                <div class="shelter-meta-row">
                    <div>📍 ${item.location || "Semarang"}</div>
                    <div>👥 Kapasitas: <strong>${item.capacityOccupied || 0} / ${item.capacityTotal || item.capacity}</strong> (${item.occupancyPercent || 25}% Terisi)</div>
                </div>
                <div class="sensor-progress-track">
                    <div class="sensor-progress-fill ${item.occupancyPercent > 50 ? 'watch' : 'safe'}" style="width: ${item.occupancyPercent || 25}%;"></div>
                </div>
                <div class="shelter-supplies">
                    📦 ${Array.isArray(item.supplies) ? item.supplies.join(" • ") : item.supplies}
                </div>
                <button type="button" class="btn-hero-primary" style="padding: 9px 14px; font-size: 12px; margin-top: 6px; justify-content: center;" onclick="window.app.navigateToShelter('${item.name}')">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg>
                    Arahkan Rute ke Posko Ini
                </button>
            </div>
        `).join("");
    }

    /* ==========================================================================
       7. Render Panduan Siaga & Batas Kendaraan
       ========================================================================== */
    renderGuidesSection() {
        const container = document.getElementById("berandaVehicleWadingGrid");
        if (!container) return;

        const vehicles = (SAFEROUTE_DATA.floodGuide && SAFEROUTE_DATA.floodGuide.vehicleThresholds) || [];
        container.innerHTML = vehicles.map(v => `
            <div class="vehicle-threshold-card">
                <div class="vehicle-icon">${v.icon || '🚗'}</div>
                <div class="vehicle-name">${v.vehicle}</div>
                <div class="vehicle-depth-badge ${v.badgeClass}">Maks ${v.maxDepth}</div>
                <div class="vehicle-note">${v.advice}</div>
            </div>
        `).join("");
    }

    /* ==========================================================================
       8. Render Live Community Feed
       ========================================================================== */
    renderCommunityFeed() {
        const container = document.getElementById("berandaCommunityFeed");
        if (!container) return;

        const feed = (SAFEROUTE_DATA.history && SAFEROUTE_DATA.history.communityFeed) || [];
        container.innerHTML = feed.map(item => `
            <div class="feed-item">
                <div class="feed-avatar">${item.author.charAt(0)}</div>
                <div class="feed-body">
                    <div class="feed-header">
                        <span class="feed-author">${item.author}</span>
                        <span class="feed-ai-badge">✓ AI Terverifikasi (${item.confidence}%)</span>
                    </div>
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-primary); margin-bottom: 2px;">📍 ${item.location} • Kedalaman ${item.depth} cm</div>
                    <div class="feed-text">${item.text}</div>
                    <div class="feed-time">${item.time}</div>
                </div>
            </div>
        `).join("");
    }

    /* ==========================================================================
       Event Listeners & Clipboard Action
       ========================================================================== */
    bindEvents() {
        // Hero CTA button to switch to map
        const btnHeroToMap = document.getElementById("btnHeroToMap");
        if (btnHeroToMap) {
            btnHeroToMap.addEventListener("click", () => {
                this.app.switchView("peta");
            });
        }

        // Hero CTA button to report flood
        const btnHeroReport = document.getElementById("btnHeroReport");
        if (btnHeroReport) {
            btnHeroReport.addEventListener("click", () => {
                this.app.openModal("modalReport");
            });
        }

        // Contact filter chips
        const chips = document.querySelectorAll(".contact-filter-chip");
        chips.forEach(chip => {
            chip.addEventListener("click", () => {
                chips.forEach(c => c.classList.remove("active"));
                chip.classList.add("active");
                this.activeContactCategory = chip.dataset.category || "all";
                this.renderContactsSection();
            });
        });
    }

    copyNumber(number, name) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(number).then(() => {
                this.app.showToast(`Nomor kontak ${name} (${number}) berhasil disalin!`);
            });
        } else {
            this.app.showToast(`Nomor: ${number}`);
        }
    }
}

if (typeof window !== "undefined") {
    window.BerandaModule = BerandaModule;
}
