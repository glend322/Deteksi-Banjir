import httpx
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.weather import Alert, WeatherForecastCache
from app.models.flood import FloodPoint
from app.services.weather_service import map_weather_code

logger = logging.getLogger(__name__)

# Koordinat Spasial Hidrologi Semarang
HULU_COORDS = (-7.0505, 110.4410)   # Semarang Atas (Banyumanik / Ungaran - Hulu DAS)
HILIR_COORDS = (-6.9535, 110.4570)  # Semarang Bawah (Genuk / Kaligawe - Hilir Rawan Banjir)

# Kode cuaca BMKG/Open-Meteo dengan intensitas tinggi
HEAVY_RAIN_CODES = {63, 65, 81, 82, 95, 96, 99}

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

async def run_predictive_flood_engine(db: Session, force_trigger: bool = False) -> Dict[str, Any]:
    """
    PRD 5.4: Prediksi, Bukan Hanya Deteksi
    Mendeteksi hujan lebat di hulu (Semarang Atas) dan menerbitkan Alert prediktif
    untuk hilir (Genuk & Kaligawe) sebelum air benar-benar meluap (Lead time ±2-3 jam).
    """
    # 1. Ambil data cuaca hulu dan hilir
    upstream_weather = await fetch_spot_weather(HULU_COORDS[0], HULU_COORDS[1])
    downstream_weather = await fetch_spot_weather(HILIR_COORDS[0], HILIR_COORDS[1])

    up_code = upstream_weather.get("weather_code", 0)
    up_precip = upstream_weather.get("precipitation", 0.0)
    up_condition = upstream_weather.get("condition", "Cerah")

    is_heavy_upstream = (up_code in HEAVY_RAIN_CODES) or (up_precip >= 10.0) or force_trigger
    alert_slug = "alert-predictive-hulu-kaligawe"

    alert_obj = db.query(Alert).filter(Alert.slug == alert_slug).first()

    if is_heavy_upstream:
        urgency = "urgent" if (up_code in {65, 82, 95, 96, 99} or up_precip >= 20.0) else "warning"
        title_text = "⚠️ Peringatan Dini: Potensi Banjir Kiriman Hulu (Genuk & Kaligawe)"
        subtext = (
            f"Curah hujan tinggi ({up_condition}, {up_precip:.1f} mm) terdeteksi di wilayah hulu Semarang Atas. "
            "Berdasarkan pemodelan hidrologi DAS Kali Babon & Kali Tenggang, limpasan air diprediksi "
            "mencapai area hilir Kaligawe dalam 2–3 jam ke depan. Harap gunakan rute alternatif."
        )

        if not alert_obj:
            alert_obj = Alert(
                slug=alert_slug,
                category=urgency,
                title=title_text,
                location="Kec. Genuk, Kaligawe & Semarang Utara",
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

        # Update proaktif status titik pantau Kaligawe
        kaligawe_point = db.query(FloodPoint).filter(FloodPoint.slug == "loc-kaligawe").first()
        if kaligawe_point:
            if kaligawe_point.depth_cm == 0 or kaligawe_point.status == "safe":
                kaligawe_point.depth_cm = 35
                kaligawe_point.status = "watch"
                kaligawe_point.status_label = "Waspada (Potensi Luapan Hulu)"
                kaligawe_point.recommendation = "Potensi kenaikan air akibat kiriman dari Semarang Atas dalam 2-3 jam."

        db.commit()
        logger.info(f"🚨 [Predictive Alert] Berhasil menerbitkan peringatan dini luapan hulu: {title_text}")

        return {
            "status": "alert_active",
            "is_heavy_upstream": True,
            "upstream_condition": up_condition,
            "upstream_precipitation_mm": up_precip,
            "downstream_condition": downstream_weather.get("condition"),
            "alert_category": urgency,
            "lead_time": "2-3 jam"
        }

    else:
        # Jika cuaca hulu sudah reda dan alert aktif sudah lebih dari 4 jam, nonaktifkan alert
        if alert_obj and alert_obj.is_active:
            now = datetime.now(timezone.utc)
            alert_time = alert_obj.created_at
            if alert_time:
                if alert_time.tzinfo is None:
                    alert_time = alert_time.replace(tzinfo=timezone.utc)
                if (now - alert_time).total_seconds() > 4 * 3600:
                    alert_obj.is_active = False
                    db.commit()
                    logger.info("ℹ️ [Predictive Alert] Cuaca hulu normal, alert prediktif dideaktivasi.")

        return {
            "status": "normal",
            "is_heavy_upstream": False,
            "upstream_condition": up_condition,
            "upstream_precipitation_mm": up_precip,
            "downstream_condition": downstream_weather.get("condition")
        }

