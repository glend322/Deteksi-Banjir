import httpx
import logging
from sqlalchemy.orm import Session
from app.models.weather import WeatherForecastCache

logger = logging.getLogger(__name__)

# Koordinat Pusat Kota Semarang
SEMARANG_LAT = -6.9932
SEMARANG_LNG = 110.4203

WEATHER_CODE_MAP = {
    0: ("Cerah", "sun"),
    1: ("Cerah Berawan", "cloud-sun"),
    2: ("Berawan", "cloud"),
    3: ("Berawan Tebal", "cloud"),
    45: ("Kabut", "cloud-fog"),
    48: ("Kabut Berembun", "cloud-fog"),
    51: ("Gerimis Ringan", "cloud-drizzle"),
    53: ("Gerimis Sedang", "cloud-drizzle"),
    55: ("Gerimis Lebat", "cloud-drizzle"),
    61: ("Hujan Ringan", "cloud-rain"),
    63: ("Hujan Sedang", "cloud-rain"),
    65: ("Hujan Lebat", "cloud-rain"),
    80: ("Hujan Lokal Ringan", "cloud-rain"),
    81: ("Hujan Lokal Sedang", "cloud-rain"),
    82: ("Hujan Sangat Lebat", "cloud-rain"),
    95: ("Hujan Petir", "cloud-lightning"),
    96: ("Hujan Petir Disertai Butiran Es", "cloud-lightning"),
    99: ("Hujan Badai Petir", "cloud-lightning"),
}

def map_weather_code(code: int):
    return WEATHER_CODE_MAP.get(code, ("Hujan Ringan", "cloud-rain"))

async def fetch_and_update_weather(db: Session) -> dict:
    """
    Mengambil data cuaca riil Kota Semarang secara live dan memperbarui database cache.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={SEMARANG_LAT}&longitude={SEMARANG_LNG}"
        f"&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
        f"&hourly=temperature_2m,weather_code&timezone=Asia%2FJakarta&forecast_days=1"
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        current = data.get("current", {})
        temp = int(round(current.get("temperature_2m", 28)))
        humidity = int(round(current.get("relative_humidity_2m", 85)))
        wind_speed_val = current.get("wind_speed_10m", 14)
        wind_speed_str = f"{int(round(wind_speed_val))} km/jam"
        weather_code = current.get("weather_code", 61)
        condition_desc, _ = map_weather_code(weather_code)

        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        codes = hourly.get("weather_code", [])

        forecast_list = []
        for i in range(0, min(len(times), 24), 3):
            time_str = times[i].split("T")[1][:5] if "T" in times[i] else f"{i:02d}:00"
            hour_temp = int(round(temps[i])) if i < len(temps) else temp
            hour_code = codes[i] if i < len(codes) else weather_code
            desc, icon = map_weather_code(hour_code)
            
            forecast_list.append({
                "time": time_str,
                "temp": hour_temp,
                "icon": icon,
                "condition": desc
            })

        cache = db.query(WeatherForecastCache).filter(WeatherForecastCache.city == "Semarang").first()
        if not cache:
            cache = WeatherForecastCache(
                city="Semarang",
                condition=condition_desc,
                temp=temp,
                humidity=humidity,
                wind_speed=wind_speed_str,
                forecast_hourly=forecast_list
            )
            db.add(cache)
        else:
            cache.condition = condition_desc
            cache.temp = temp
            cache.humidity = humidity
            cache.wind_speed = wind_speed_str
            cache.forecast_hourly = forecast_list

        db.commit()
        db.refresh(cache)
        logger.info(f"✅ Data cuaca Semarang berhasil diperbarui: {condition_desc}, {temp}°C, {humidity}%")
        return {
            "city": "Semarang",
            "condition": condition_desc,
            "temp": temp,
            "humidity": humidity,
            "wind_speed": wind_speed_str,
            "forecast_hourly": forecast_list,
            "status": "updated_from_live_api"
        }

    except Exception as e:
        logger.error(f"❌ Gagal mengambil data cuaca live: {e}")
        existing = db.query(WeatherForecastCache).filter(WeatherForecastCache.city == "Semarang").first()
        if existing:
            return {
                "city": existing.city,
                "condition": existing.condition,
                "temp": existing.temp,
                "humidity": existing.humidity,
                "wind_speed": existing.wind_speed,
                "forecast_hourly": existing.forecast_hourly or [],
                "status": "fallback_from_db"
            }
        return {"status": "error", "detail": str(e)}


def get_semarang_area_name(lat: float, lng: float) -> str:
    """Estimasi nama wilayah di Semarang berdasarkan koordinat GPS."""
    if lat > -6.97:
        return "Genuk, Semarang" if lng > 110.43 else "Semarang Utara"
    elif -7.01 < lat <= -6.97:
        if lng <= 110.40:
            return "Semarang Barat"
        elif lng <= 110.43:
            return "Semarang Tengah"
        else:
            return "Semarang Timur"
    elif -7.05 < lat <= -7.01:
        return "Candisari, Semarang" if lng <= 110.43 else "Gayamsari, Semarang"
    elif lat <= -7.05:
        return "Banyumanik, Semarang" if lng <= 110.43 else "Tembalang, Semarang"
    return "Kota Semarang"


async def fetch_weather_by_coords(lat: float, lng: float) -> dict:
    """Mengambil data cuaca real-time & per jam untuk koordinat GPS spesifik."""
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lng}"
        f"&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
        f"&hourly=temperature_2m,weather_code&timezone=Asia%2FJakarta&forecast_days=2"
    )
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        current = data.get("current", {})
        temp = int(round(current.get("temperature_2m", 27)))
        humidity = int(round(current.get("relative_humidity_2m", 85)))
        wind_speed_val = current.get("wind_speed_10m", 12)
        wind_speed_str = f"{int(round(wind_speed_val))} km/jam"
        weather_code = current.get("weather_code", 61)
        condition_desc, _ = map_weather_code(weather_code)

        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        codes = hourly.get("weather_code", [])

        forecast_list = []
        now_hour_prefix = ""
        try:
            from datetime import datetime
            import zoneinfo
            now_hour_prefix = datetime.now(zoneinfo.ZoneInfo("Asia/Jakarta")).strftime("%Y-%m-%dT%H")
        except Exception:
            pass

        start_idx = 0
        if now_hour_prefix:
            for i, t in enumerate(times):
                if t.startswith(now_hour_prefix):
                    start_idx = i
                    break

        for i in range(start_idx, min(start_idx + 8, len(times))):
            t_str = times[i].split("T")[1][:5].replace(":", ".") if "T" in times[i] else f"{i:02d}.00"
            hour_temp = int(round(temps[i])) if i < len(temps) else temp
            hour_code = codes[i] if i < len(codes) else weather_code
            desc, icon = map_weather_code(hour_code)
            forecast_list.append({
                "time": t_str,
                "temp": hour_temp,
                "icon": icon,
                "condition": desc
            })

        return {
            "city": get_semarang_area_name(lat, lng),
            "condition": condition_desc,
            "temp": temp,
            "humidity": humidity,
            "wind_speed": wind_speed_str,
            "forecast_hourly": forecast_list,
            "status": "live_gps"
        }
    except Exception as e:
        logger.warning(f"Gagal mengambil cuaca koordinat ({lat}, {lng}): {e}")
        return None


