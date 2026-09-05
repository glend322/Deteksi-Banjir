from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.weather import Alert, WeatherForecastCache
from app.schemas.weather import WeatherResponse, AlertResponse, EmergencyContact, EducationGuide, HourlyForecast

from app.services.weather_service import fetch_and_update_weather
from app.services.predictive_service import run_predictive_flood_engine
from app.services.decay_service import apply_confidence_decay

router = APIRouter()

@router.post("/sync", summary="Sinkronisasi Cuaca Live Semarang (BMKG/Open-Meteo)")
async def sync_live_weather(db: Session = Depends(get_db)):
    """Memicu pembaruan data cuaca riil Kota Semarang secara langsung."""
    result = await fetch_and_update_weather(db)
    return result

@router.post("/run-predictive-engine", summary="Trigger Prediksi Dini Banjir & Confidence Decay")
async def trigger_predictive_engine(force_trigger: bool = False, db: Session = Depends(get_db)):
    """
    Memicu kalkulasi prediktif hidrologi DAS Semarang hulu -> hilir (PRD 5.4)
    serta memperbarui confidence decay data banjir (PRD 5.5).
    """
    decay_res = apply_confidence_decay(db)
    predictive_res = await run_predictive_flood_engine(db, force_trigger=force_trigger)
    return {
        "status": "success",
        "decay_summary": decay_res,
        "predictive_summary": predictive_res
    }

@router.get("/current", response_model=WeatherResponse)
def get_current_weather(db: Session = Depends(get_db)):
    # Ambil dari cache atau return data default BMKG Semarang
    cache = db.query(WeatherForecastCache).filter(WeatherForecastCache.city == "Semarang").first()
    if cache and cache.forecast_hourly:
        forecast = [HourlyForecast(**f) for f in cache.forecast_hourly]
        return WeatherResponse(
            city=cache.city,
            condition=cache.condition,
            temp=cache.temp,
            humidity=cache.humidity,
            wind_speed=cache.wind_speed,
            forecast_hourly=forecast
        )

    # Fallback BMKG data
    default_forecast = [
        HourlyForecast(time="09:00", temp=26, icon="cloud-drizzle", condition="Gerimis"),
        HourlyForecast(time="11:00", temp=27, icon="cloud-rain", condition="Hujan Sedang"),
        HourlyForecast(time="13:00", temp=28, icon="cloud-rain", condition="Hujan Lebat"),
        HourlyForecast(time="15:00", temp=27, icon="cloud-lightning", condition="Hujan Petir"),
        HourlyForecast(time="17:00", temp=26, icon="cloud-rain", condition="Hujan Ringan"),
        HourlyForecast(time="19:00", temp=25, icon="cloud", condition="Berawan")
    ]
    return WeatherResponse(
        city="Semarang",
        condition="Hujan Ringan",
        temp=27,
        humidity=86,
        wind_speed="14 km/jam",
        forecast_hourly=default_forecast
    )

@router.get("/alerts", response_model=List[AlertResponse])
def get_active_alerts(db: Session = Depends(get_db)):
    alerts = db.query(Alert).filter(Alert.is_active == True).order_by(Alert.created_at.desc()).all()
    return alerts

@router.get("/emergency-contacts", response_model=List[EmergencyContact])
def get_emergency_contacts():
    return [
        EmergencyContact(name="Panggilan Darurat Terpadu Kota Semarang", number="112", desc="Bebas Pulsa 24 Jam (Ambulans, BPBD, Polisi, Damkar)"),
        EmergencyContact(name="Pusdalops BPBD Kota Semarang", number="024-3580007", desc="Evakuasi banjir, logistik pengungsian, perahu karet"),
        EmergencyContact(name="Kantor SAR / Basarnas Semarang", number="024-7607777", desc="Penyelamatan darurat & evakuasi air deras"),
        EmergencyContact(name="Dinas Pemadam Kebakaran Semarang", number="113", desc="Pompa penyedot darurat & pembersihan material"),
        EmergencyContact(name="Palang Merah Indonesia (PMI) Semarang", number="024-3541237", desc="Bantuan medis pertama & ambulans")
    ]

@router.get("/education/guides", response_model=EducationGuide)
def get_education_guides():
    return EducationGuide(
        before=[
            "Pantau terus peta SafeRoute dan perkiraan cuaca BMKG Kota Semarang.",
            "Simpan dokumen penting dan barang berharga di tempat yang tinggi atau plastik kedap air.",
            "Ketahui letak MCB listrik dan matikan bila air mulai memasuki pemukiman.",
            "Cek kendaraan: pastikan rem, filter udara, dan knalpot dalam kondisi optimal."
        ],
        during=[
            "JANGAN memaksakan menerobos banjir bila kedalaman melebihi batas ground clearance kendaraan (>30 cm untuk motor/sedan).",
            "Bila kendaraan mogok di tengah banjir, segera tinggalkan kendaraan dan berjalan ke tempat yang lebih tinggi.",
            "Hindari menyentuh tiang listrik, kabel jatuh, atau papan reklame berlistrik.",
            "Buka rute SafeRoute untuk menemukan titik posko evakuasi terdekat yang aktif."
        ],
        after=[
            "Jangan langsung menyalakan mesin kendaraan yang sempat terendam sebelum oli dan kelistrikan dicek mekanik.",
            "Gunakan alas kaki anti robek saat membersihkan sisa lumpur banjir untuk menghindari infeksi Leptospirosis.",
            "Laporkan kondisi terkini jalan Anda melalui fitur Laporkan Banjir SafeRoute guna membantu warga lain."
        ],
        vehicle_thresholds=[
            {"vehicle": "Motor Bebek / Matic", "maxDepth": "20 cm", "advice": "Air setinggi knalpot / filter udara, jangan dipaksakan."},
            {"vehicle": "Mobil Sedan / City Car", "maxDepth": "30 cm", "advice": "Batas bawah bumper; air bisa masuk ke ruang mesin."},
            {"vehicle": "Mobil SUV / MPV Tinggi", "maxDepth": "50 cm", "advice": "Jaga putaran gas stabil pada gigi rendah, jangan lepas pedal gas mendadak."},
            {"vehicle": "Truk / Kendaraan Khusus", "maxDepth": "70 cm", "advice": "Tetap waspada terhadap lubang jalan tak terlihat di bawah air."}
        ]
    )

