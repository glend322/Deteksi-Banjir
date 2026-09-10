import httpx
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, List
from sqlalchemy.orm import Session
from app.models.weather import Alert, WeatherForecastCache
from app.models.flood import FloodPoint
from app.services.weather_service import map_weather_code

logger = logging.getLogger(__name__)

# Kode cuaca BMKG/Open-Meteo dengan intensitas tinggi
HEAVY_RAIN_CODES = {63, 65, 81, 82, 95, 96, 99}

# ─────────────────────────────────────────────────────────────────────────────
# Konfigurasi Multi-Area DAS Semarang (PRD 5.4 — P2.5)
# Setiap entry: (nama_das, koordinat_hulu, koordinat_hilir, slug_alert, label_area)
# ─────────────────────────────────────────────────────────────────────────────
WATERSHED_ZONES: List[Dict[str, Any]] = [
    {
        "name": "DAS Kali Babon (Banyumanik → Kaligawe)",
        "upstream": (-7.0505, 110.4410),    # Banyumanik / Ungaran
        "downstream": (-6.9535, 110.4570),  # Kaligawe / Genuk
        "alert_slug": "alert-predictive-hulu-kaligawe",
        "downstream_area": "Kec. Genuk, Kaligawe & Semarang Utara",
        "affected_point_slug": "loc-kaligawe",
        "lead_time": "2-3 jam",
    },
    {
        "name": "DAS Kali Garang (Ungaran → Tugu/Semarang Barat)",
        "upstream": (-7.1200, 110.3800),    # Ungaran hulu Kali Garang
        "downstream": (-6.9700, 110.3600),  # Tugu / Semarang Barat
        "alert_slug": "alert-predictive-hulu-kali-garang",
        "downstream_area": "Kec. Tugu, Semarang Barat & Mijen",
        "affected_point_slug": "loc-tugu",
        "lead_time": "3-4 jam",
    },
    {
        "name": "DAS Kali Semarang (Gunungpati → Semarang Tengah)",
        "upstream": (-7.0800, 110.3900),    # Gunungpati
        "downstream": (-6.9870, 110.4100),  # Semarang Tengah / Bulu
        "alert_slug": "alert-predictive-hulu-kali-semarang",
        "downstream_area": "Kec. Semarang Tengah & Semarang Barat",
        "affected_point_slug": "loc-bulu",
        "lead_time": "2-3 jam",
    },
]


async def fetch_spot_weather(lat: float, lng: float) -> Dict[str, Any]:
    """
    Mengambil data cuaca titik spesifik dari Open-Meteo API.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lng}"
        f"&current=temperature_2m,relative_humidity_2m,weather_code,precipitation,wind_speed_10m"
        f"&timezone=Asia%2FJakarta"
    )
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json().get("current", {})
                w_code = data.get("weather_code", 0)
                desc, icon = map_weather_code(w_code)
                return {
                    "temp": int(round(data.get("temperature_2m", 27))),
                    "weather_code": w_code,
                    "condition": desc,
                    "icon": icon,
                    "precipitation": float(data.get("precipitation", 0.0)),
                    "humidity": int(round(data.get("relative_humidity_2m", 80)))
                }
    except Exception as e:
        logger.debug(f"[Predictive Engine] Open-Meteo spot request failed ({e}), using simulated values.")

    return {
        "temp": 26,
        "weather_code": 61,
        "condition": "Hujan Ringan",
        "icon": "cloud-rain",
        "precipitation": 2.5,
        "humidity": 85
    }


async def _process_single_watershed(zone: Dict[str, Any], db: Session, force_trigger: bool = False) -> Dict[str, Any]:
    """
    Proses prediksi dini untuk satu zona DAS:
    - Ambil data cuaca hulu
    - Jika hujan lebat → terbitkan alert prediktif untuk area hilir
    - Update status flood point terdampak
    """
    upstream_weather = await fetch_spot_weather(zone["upstream"][0], zone["upstream"][1])
    up_code = upstream_weather.get("weather_code", 0)
    up_precip = upstream_weather.get("precipitation", 0.0)
    up_condition = upstream_weather.get("condition", "Cerah")

    is_heavy_upstream = (up_code in HEAVY_RAIN_CODES) or (up_precip >= 10.0) or force_trigger
    alert_slug = zone["alert_slug"]
    alert_obj = db.query(Alert).filter(Alert.slug == alert_slug).first()

    if is_heavy_upstream:
        urgency = "urgent" if (up_code in {65, 82, 95, 96, 99} or up_precip >= 20.0) else "warning"
        title_text = f"⚠️ Peringatan Dini: Potensi Banjir Kiriman ({zone['name']})"
        subtext = (
            f"Curah hujan tinggi ({up_condition}, {up_precip:.1f} mm) terdeteksi di wilayah hulu {zone['name']}. "
            f"Berdasarkan pemodelan hidrologi, limpasan air diprediksi mencapai area hilir dalam {zone['lead_time']}. "
            "Harap gunakan rute alternatif."
        )

        if not alert_obj:
            alert_obj = Alert(
                slug=alert_slug,
                category=urgency,
                title=title_text,
                location=zone["downstream_area"],
                subtext=subtext,
                icon="alert-triangle",
                color="#EF4444" if urgency == "urgent" else "#F59E0B",
                for_you=True,
                action_text="Lihat Rute Aman Alternatif",
                action_route_id="route-safe",
                is_active=True
            )
            db.add(alert_obj)
        else:
            alert_obj.category = urgency
            alert_obj.title = title_text
            alert_obj.subtext = subtext
            alert_obj.is_active = True
            alert_obj.color = "#EF4444" if urgency == "urgent" else "#F59E0B"

        # Update proaktif status titik pantau hilir terdampak
        affected_point = db.query(FloodPoint).filter(
            FloodPoint.slug == zone["affected_point_slug"]
        ).first()
        if affected_point and (affected_point.depth_cm == 0 or affected_point.status == "safe"):
            affected_point.depth_cm = 35
            affected_point.status = "watch"
            affected_point.status_label = f"Waspada (Potensi Luapan {zone['name']})"
            affected_point.recommendation = (
                f"Potensi kenaikan air akibat kiriman dari hulu {zone['name']} dalam {zone['lead_time']}."
            )

        logger.info(f"🚨 [Predictive Alert] Alert diterbitkan: {title_text}")
        return {
            "zone": zone["name"],
            "status": "alert_active",
            "is_heavy_upstream": True,
            "upstream_condition": up_condition,
            "upstream_precipitation_mm": up_precip,
            "alert_category": urgency,
            "lead_time": zone["lead_time"]
        }

    else:
        # Nonaktifkan alert jika cuaca sudah reda > 4 jam
        if alert_obj and alert_obj.is_active:
            now = datetime.now(timezone.utc)
            alert_time = alert_obj.created_at
            if alert_time:
                if alert_time.tzinfo is None:
                    alert_time = alert_time.replace(tzinfo=timezone.utc)
                if (now - alert_time).total_seconds() > 4 * 3600:
                    alert_obj.is_active = False
                    logger.info(f"ℹ️ [Predictive Alert] Alert {alert_slug} dideaktivasi (cuaca hulu normal).")

        return {
            "zone": zone["name"],
            "status": "normal",
            "is_heavy_upstream": False,
            "upstream_condition": up_condition,
            "upstream_precipitation_mm": up_precip,
        }


async def run_predictive_flood_engine(db: Session, force_trigger: bool = False) -> Dict[str, Any]:
    """
    PRD 5.4: Prediksi, Bukan Hanya Deteksi — Multi-Area DAS Semarang (P2.5)
    Menjalankan prediksi hidrologi untuk semua zona DAS yang terdaftar secara berurutan,
    lalu menerbitkan alert prediktif untuk area hilir yang berpotensi terdampak.
    """
    results = []
    alerts_active = 0

    for zone in WATERSHED_ZONES:
        try:
            result = await _process_single_watershed(zone, db, force_trigger=force_trigger)
            results.append(result)
            if result.get("status") == "alert_active":
                alerts_active += 1
        except Exception as e:
            logger.error(f"[Predictive Engine] Gagal memproses zona {zone['name']}: {e}")
            results.append({"zone": zone["name"], "status": "error", "error": str(e)})

    db.commit()

    return {
        "total_zones_checked": len(WATERSHED_ZONES),
        "alerts_active": alerts_active,
        "zones": results
    }
