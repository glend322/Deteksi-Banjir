/**
 * SafeRoute - Weather Module
 * Menampilkan info cuaca real-time berbasis GPS di atas peta (Google Maps style).
 */

class WeatherModule {
    constructor(app) {
        this.app = app;
        this._cardVisible = false;

        /* Element refs (diisi saat init) */
        this._pill      = null;
        this._card      = null;
        this._closeBtn  = null;

        /* Data cuaca terakhir (untuk re-render) */
        this._lastData  = null;

        /* Mapping kode ikon backend → emoji */
        this.ICON_MAP = {
            'sun':              '☀️',
            'cloud-sun':        '⛅',
            'cloud':            '☁️',
            'cloud-drizzle':    '🌦️',
            'cloud-rain':       '🌧️',
            'cloud-lightning':  '⛈️',
            'cloud-fog':        '🌫️',
            'snow':             '❄️',
        };

        /* SVG besar untuk panel cuaca saat ini */
        this.ICON_SVG = {
            'sun': `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" width="56" height="56">
                        <circle cx="32" cy="32" r="12" fill="#FBBF24"/>
                        <g stroke="#FBBF24" stroke-width="3" stroke-linecap="round">
                            <line x1="32" y1="4"  x2="32" y2="12"/>
                            <line x1="32" y1="52" x2="32" y2="60"/>
                            <line x1="4"  y1="32" x2="12" y2="32"/>
                            <line x1="52" y1="32" x2="60" y2="32"/>
                            <line x1="11" y1="11" x2="17" y2="17"/>
                            <line x1="47" y1="47" x2="53" y2="53"/>
                            <line x1="53" y1="11" x2="47" y2="17"/>
                            <line x1="17" y1="47" x2="11" y2="53"/>
                        </g>
                    </svg>`,
            'cloud-sun': `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" width="56" height="56">
                        <circle cx="22" cy="22" r="10" fill="#FBBF24"/>
                        <path d="M14 36a10 10 0 0 1 10-10h2a12 12 0 0 1 12 12v2H14v-4z" fill="#D1D5DB"/>
                        <rect x="10" y="38" width="36" height="12" rx="6" fill="#9CA3AF"/>
                    </svg>`,
            'cloud': `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" width="56" height="56">
                        <path d="M10 38a14 14 0 0 1 14-14 14 14 0 0 1 13.5 10A10 10 0 0 1 44 54H14A10 10 0 0 1 10 38z" fill="#9CA3AF"/>
                    </svg>`,
            'cloud-drizzle': `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" width="56" height="56">
                        <path d="M10 30a14 14 0 0 1 14-14 14 14 0 0 1 13.5 10A10 10 0 0 1 44 46H14A10 10 0 0 1 10 30z" fill="#93C5FD"/>
                        <g stroke="#3B82F6" stroke-width="2.5" stroke-linecap="round">
                            <line x1="20" y1="52" x2="18" y2="60"/>
                            <line x1="32" y1="52" x2="30" y2="60"/>
                        </g>
                    </svg>`,
            'cloud-rain': `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" width="56" height="56">
                        <path d="M8 28a16 16 0 0 1 16-16 16 16 0 0 1 15.4 12A11 11 0 0 1 46 44H14A11 11 0 0 1 8 28z" fill="#60A5FA"/>
                        <g stroke="#1D4ED8" stroke-width="2.5" stroke-linecap="round">
                            <line x1="18" y1="50" x2="14" y2="60"/>
                            <line x1="30" y1="50" x2="26" y2="60"/>
                            <line x1="42" y1="50" x2="38" y2="60"/>
                        </g>
                    </svg>`,
            'cloud-lightning': `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" width="56" height="56">
                        <path d="M8 28a16 16 0 0 1 16-16 16 16 0 0 1 15.4 12A11 11 0 0 1 46 44H14A11 11 0 0 1 8 28z" fill="#94A3B8"/>
                        <polygon points="30,46 24,56 32,54 26,64 36,50 28,52" fill="#FBBF24"/>
                    </svg>`,
            'cloud-fog': `<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" width="56" height="56">
                        <path d="M10 24a14 14 0 0 1 14-14 14 14 0 0 1 13.5 10A10 10 0 0 1 44 40H14A10 10 0 0 1 10 24z" fill="#D1D5DB"/>
                        <g stroke="#9CA3AF" stroke-width="2.5" stroke-linecap="round">
                            <line x1="10" y1="48" x2="50" y2="48"/>
                            <line x1="14" y1="56" x2="46" y2="56"/>
                        </g>
                    </svg>`,
        };
    }

    /* ------------------------------------------------------------------ */
    /*  init — dipanggil otomatis oleh app.js                              */
    /* ------------------------------------------------------------------ */
    init() {
        /* Topbar weather button (existing feature) */
        const topbarWeather = document.getElementById('weatherWidgetBtn');
        if (topbarWeather) {
            topbarWeather.addEventListener('click', () => {
                this.app.openModal('modalWeather');
            });
        }

        /* Referensi ke elemen cuaca di peta */
        this._pill     = document.getElementById('mapWeatherPill');
        this._card     = document.getElementById('mapWeatherCard');
        this._closeBtn = document.getElementById('btnMapWeatherClose');

        if (!this._pill || !this._card) return; /* Jika belum di view peta, skip */

        /* Klik pill → toggle card */
        this._pill.addEventListener('click', () => this._toggleCard());
        this._pill.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this._toggleCard(); }
        });

        /* Tombol tutup card */
        if (this._closeBtn) {
            this._closeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this._hideCard();
            });
        }

        /* Klik di luar card → tutup */
        document.addEventListener('click', (e) => {
            if (this._cardVisible &&
                !this._card.contains(e.target) &&
                !this._pill.contains(e.target)) {
                this._hideCard();
            }
        });

        /* Ambil dan tampilkan data cuaca */
        this.fetchAndRenderWeather();
    }

    /* ------------------------------------------------------------------ */
    /*  Toggle, show, hide card                                            */
    /* ------------------------------------------------------------------ */
    _toggleCard() {
        this._cardVisible ? this._hideCard() : this._showCard();
    }

    _showCard() {
        if (!this._card) return;
        this._card.style.display = 'block';
        /* Trigger animation */
        this._card.style.animation = 'none';
        void this._card.offsetWidth; /* reflow */
        this._card.style.animation  = '';
        this._cardVisible = true;
    }

    _hideCard() {
        if (!this._card) return;
        this._card.style.display = 'none';
        this._cardVisible = false;
    }

    /* ------------------------------------------------------------------ */
    /*  GPS + Fetch                                                        */
    /* ------------------------------------------------------------------ */
    fetchAndRenderWeather() {
        if (!navigator.geolocation) {
            this._fetchWeatherData(null, null);
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (pos) => {
                this._fetchWeatherData(pos.coords.latitude, pos.coords.longitude);
            },
            () => {
                /* Izin ditolak atau timeout → pakai default Semarang */
                this._fetchWeatherData(null, null);
            },
            { timeout: 8000 }
        );
    }

    _fetchWeatherData(lat, lng) {
        let url = '/api/weather/current';
        if (lat !== null && lng !== null) {
            url += `?lat=${lat.toFixed(6)}&lng=${lng.toFixed(6)}`;
        }

        fetch(url)
            .then((res) => {
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return res.json();
            })
            .then((data) => {
                this._renderWeather(data);
            })
            .catch(() => {
                /* Backend tidak tersedia → gunakan data statis lokal */
                const fallback = window.SAFEROUTE_WEATHER_DATA;
                if (fallback) {
                    const mapped = {
                        city:           fallback.city      || 'Semarang',
                        condition:      fallback.condition || 'Cerah',
                        temp:           fallback.temp      || 28,
                        icon:           fallback.icon      || 'cloud-sun',
                        forecast_hourly: (fallback.forecastHourly || []).map((h) => ({
                            time:      h.time,
                            temp:      h.temp,
                            icon:      h.icon,
                            condition: h.condition,
                        })),
                    };
                    this._renderWeather(mapped);
                }
            });
    }

    /* ------------------------------------------------------------------ */
    /*  Render                                                             */
    /* ------------------------------------------------------------------ */
    _renderWeather(data) {
        this._lastData = data;

        const emoji = this._getEmoji(data.icon || data.condition);
        const temp  = `${data.temp}°C`;
        const city  = data.city || 'Semarang';

        /* ---- Pill ---- */
        this._setInner('mapWeatherPillIcon', emoji);
        this._setInner('mapWeatherPillTemp', temp);
        this._setInner('mapWeatherPillCity', city);

        /* ---- Card header ---- */
        this._setInner('mapWeatherCardCity', city);

        /* ---- Card current weather ---- */
        this._setInner('mapWeatherCardTemp', temp);
        this._setInner('mapWeatherCardCondition', data.condition || '');

        /* ---- Card icon (large SVG) ---- */
        const iconEl = document.getElementById('mapWeatherCardIcon');
        if (iconEl) {
            const svgKey = data.icon || 'cloud-rain';
            iconEl.innerHTML = this.ICON_SVG[svgKey] || `<span style="font-size:48px">${emoji}</span>`;
        }

        /* ---- Hourly forecast strip ---- */
        this._renderHourly(data.forecast_hourly || []);
    }

    _renderHourly(forecastList) {
        const track = document.getElementById('mapWeatherHourlyTrack');
        if (!track) return;

        if (!forecastList || forecastList.length === 0) {
            track.innerHTML = '<p style="font-size:12px;color:#94a3b8;padding:8px">Tidak ada data jam-an.</p>';
            return;
        }

        const html = forecastList.map((item) => {
            const emoji = this._getEmoji(item.icon || '');
            const time  = item.time ? String(item.time).replace('.', ':') : '--:--';
            const temp  = item.temp !== undefined ? `${item.temp}°` : '--°';
            return `<div class="hourly-col">
                        <div class="hourly-time">${time}</div>
                        <div class="hourly-icon-box">${emoji}</div>
                        <div class="hourly-temp">${temp}</div>
                    </div>`;
        }).join('');

        track.innerHTML = html;
    }

    /* ------------------------------------------------------------------ */
    /*  Helper                                                             */
    /* ------------------------------------------------------------------ */
    _getEmoji(iconCode) {
        if (!iconCode) return '🌤️';
        const key = String(iconCode).toLowerCase();
        /* Coba pencocokan langsung */
        if (this.ICON_MAP[key]) return this.ICON_MAP[key];
        /* Pencocokan sebagian */
        for (const [k, v] of Object.entries(this.ICON_MAP)) {
            if (key.includes(k) || k.includes(key)) return v;
        }
        return '🌤️';
    }

    _setInner(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }
}

if (typeof window !== 'undefined') {
    window.WeatherModule = WeatherModule;
}
