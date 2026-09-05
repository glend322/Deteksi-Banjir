import sys
import os
from shapely.geometry import Point, Polygon
from geoalchemy2.shape import from_shape

# Tambahkan path root ke sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal, Base, engine, init_postgis
from app.core.security import get_password_hash
from app.models.user import User, SavedLocation, TripHistory
from app.models.flood import FloodPoint, FloodZone, EvacuationPoint, EnvironmentalRiskPoint
from app.models.report import FloodReport
from app.models.weather import Alert, WeatherForecastCache

def seed_database():
    print("🚀 Memulai proses inisialisasi dan seeding database SafeRoute Semarang...")
    
    # Inisialisasi ekstensi PostGIS dan buat tabel
    init_postgis()
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 1. Bersihkan data lama (opsional jika reset)
        db.query(SavedLocation).delete()
        db.query(TripHistory).delete()
        db.query(FloodReport).delete()
        db.query(FloodPoint).delete()
        db.query(FloodZone).delete()
        db.query(EvacuationPoint).delete()
        db.query(EnvironmentalRiskPoint).delete()
        db.query(Alert).delete()
        db.query(WeatherForecastCache).delete()
        db.query(User).delete()
        db.commit()

        # 2. Seed User Demo (Andi Pratama)
        user = User(
            email="andi.pratama@gmail.com",
            hashed_password=get_password_hash("password123"),
            full_name="Andi Pratama",
            avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
            vehicle_type="Mobil (City Car)",
            vehicle_max_depth_cm=35,
            is_active=True,
            is_admin=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # 3. Seed Saved Locations
        saved_locs_data = [
            {"name": "Rumah", "address": "Jl. Ngesrep Timur V, Banyumanik", "icon": "home", "lat": -7.0505, "lng": 110.4410},
            {"name": "Kantor", "address": "Jl. Pemuda No. 142, Semarang Tengah", "icon": "briefcase", "lat": -6.9800, "lng": 110.4180},
            {"name": "Kampus Undip", "address": "Jl. Prof. Soedarto, Tembalang", "icon": "graduation-cap", "lat": -7.0520, "lng": 110.4450}
        ]
        for loc in saved_locs_data:
            geom = from_shape(Point(loc["lng"], loc["lat"]), srid=4326)
            db.add(SavedLocation(user_id=user.id, name=loc["name"], address=loc["address"], icon=loc["icon"], geom=geom))

        # 4. Seed Flood Points (Titik Pantau Banjir Semarang)
        flood_points_data = [
            {
                "slug": "loc-kaligawe",
                "name": "Jl. Kaligawe Raya",
                "area": "Genuk, Semarang",
                "lat": -6.9535,
                "lng": 110.4570,
                "status": "impassable",
                "status_label": "Tidak Dapat Dilalui",
                "depth_cm": 60,
                "source": "CCTV Dinas PU",
                "confidence": 96,
                "image_url": "/assets/cctv_kaligawe.jpg",
                "recommendation": "Hindari rute ini. Gunakan rute alternatif via Tol Gayamsari atau Jl. Wolter Monginsidi.",
                "vehicles_allowed": ["Hanya Truk Besar / SAR"],
                "cause": "Curah hujan hulu tinggi & pasang air laut (Rob)"
            },
            {
                "slug": "loc-genuk",
                "name": "Kecamatan Genuk (Jl. Wolter Monginsidi)",
                "area": "Genuk, Semarang Timur",
                "lat": -6.9620,
                "lng": 110.4735,
                "status": "flooded",
                "status_label": "Tergenang",
                "depth_cm": 38,
                "source": "Laporan Warga (Terverifikasi AI)",
                "confidence": 88,
                "image_url": "/assets/cctv_kaligawe.jpg",
                "recommendation": "Motor tidak disarankan lewat. Mobil ber-ground clearance tinggi harap pelan-pelan.",
                "vehicles_allowed": ["Mobil SUV", "Truk"],
                "cause": "Drainase tersumbat & limpasan kali Babon"
            },
            {
                "slug": "loc-tambakrejo",
                "name": "Tambakrejo / Pelabuhan Tanjung Emas",
                "area": "Semarang Utara",
                "lat": -6.9450,
                "lng": 110.4350,
                "status": "flooded",
                "status_label": "Tergenang",
                "depth_cm": 32,
                "source": "Sensor IoT BMKG Maritim",
                "confidence": 92,
                "image_url": "/assets/cctv_kaligawe.jpg",
                "recommendation": "Rob pasang laut naik. Arus air cukup deras di tepi dermaga.",
                "vehicles_allowed": ["Mobil Tinggi", "Truk"],
                "cause": "Pasang Air Laut Maksimum (Rob)"
            },
            {
                "slug": "loc-mangkang",
                "name": "Jl. Raya Mangkang - Tugu",
                "area": "Tugu, Semarang Barat",
                "lat": -6.9745,
                "lng": 110.3320,
                "status": "watch",
                "status_label": "Waspada",
                "depth_cm": 18,
                "source": "CCTV Dishub Semarang",
                "confidence": 84,
                "image_url": "/assets/cctv_kaligawe.jpg",
                "recommendation": "Genangan tipis 15-18 cm di lajur kiri arah barat. Masih bisa dilalui perlahan.",
                "vehicles_allowed": ["Semua Kendaraan"],
                "cause": "Limpasan air sawah & hujan lokal"
            },
            {
                "slug": "loc-gayamsari",
                "name": "Simpang Gayamsari / Jl. Majapahit",
                "area": "Gayamsari, Semarang",
                "lat": -6.9940,
                "lng": 110.4530,
                "status": "watch",
                "status_label": "Waspada",
                "depth_cm": 15,
                "source": "Laporan Warga",
                "confidence": 79,
                "image_url": "/assets/cctv_kaligawe.jpg",
                "recommendation": "Antrean padat dekat jembatan tol. Kurangi kecepatan.",
                "vehicles_allowed": ["Semua Kendaraan"],
                "cause": "Drainase lambat"
            },
            {
                "slug": "loc-simpanglima",
                "name": "Kawasan Simpang Lima & Jl. Pahlawan",
                "area": "Semarang Tengah",
                "lat": -6.9904,
                "lng": 110.4229,
                "status": "safe",
                "status_label": "Aman",
                "depth_cm": 0,
                "source": "CCTV Smart City",
                "confidence": 99,
                "image_url": "/assets/cctv_kaligawe.jpg",
                "recommendation": "Jalan bebas genangan. Kondisi lalu lintas ramai lancar.",
                "vehicles_allowed": ["Semua Kendaraan"],
                "cause": "Sistem pompa polder aktif normal"
            },
            {
                "slug": "loc-tembalang",
                "name": "Kawasan Undip & Banyumanik",
                "area": "Semarang Atas",
                "lat": -7.0505,
                "lng": 110.4410,
                "status": "safe",
                "status_label": "Aman",
                "depth_cm": 0,
                "source": "Sensor IoT",
                "confidence": 100,
                "recommendation": "Dataran tinggi, bebas dari risiko banjir.",
                "vehicles_allowed": ["Semua Kendaraan"],
                "cause": "Elevasi >180 mdpl"
            }
        ]
        for p in flood_points_data:
            geom = from_shape(Point(p["lng"], p["lat"]), srid=4326)
            db.add(FloodPoint(
                slug=p["slug"],
                name=p["name"],
                area=p["area"],
                status=p["status"],
                status_label=p["status_label"],
                depth_cm=p["depth_cm"],
                source=p["source"],
                confidence=p["confidence"],
                image_url=p.get("image_url", "/assets/cctv_kaligawe.jpg"),
                recommendation=p["recommendation"],
                vehicles_allowed=p.get("vehicles_allowed", []),
                cause=p.get("cause"),
                geom=geom
            ))

        # 5. Seed Flood Zones (Poligon PRD: Fill Biru + Outline Merah)
        flood_zones_data = [
            {
                "slug": "poly-kaligawe",
                "name": "Zona Merah Kaligawe - Genuk",
                "status": "impassable",
                "fill_color": "#3B82F6",
                "fill_opacity": "0.45",
                "border_color": "#EF4444",
                "border_weight": 3,
                "coordinates": [
                    [-6.945, 110.445],
                    [-6.942, 110.472],
                    [-6.960, 110.485],
                    [-6.968, 110.468],
                    [-6.958, 110.448],
                    [-6.945, 110.445] # Tutup poligon
                ]
            },
            {
                "slug": "poly-semarang-utara",
                "name": "Zona Tergenang Semarang Utara & Pelabuhan",
                "status": "flooded",
                "fill_color": "#3B82F6",
                "fill_opacity": "0.35",
                "border_color": "#EF4444",
                "border_weight": 2,
                "coordinates": [
                    [-6.938, 110.415],
                    [-6.935, 110.445],
                    [-6.955, 110.440],
                    [-6.952, 110.410],
                    [-6.938, 110.415]
                ]
            },
            {
                "slug": "poly-tugu",
                "name": "Zona Waspada Aliran Kali Beringin",
                "status": "watch",
                "fill_color": "#3B82F6",
                "fill_opacity": "0.20",
                "border_color": "#F59E0B",
                "border_weight": 2,
                "coordinates": [
                    [-6.968, 110.320],
                    [-6.965, 110.345],
                    [-6.980, 110.342],
                    [-6.985, 110.318],
                    [-6.968, 110.320]
                ]
            }
        ]
        for z in flood_zones_data:
            # Shapely Polygon membutuhkan koordinat (lng, lat)
            poly_coords = [(pt[1], pt[0]) for pt in z["coordinates"]]
            geom = from_shape(Polygon(poly_coords), srid=4326)
            db.add(FloodZone(
                slug=z["slug"],
                name=z["name"],
                status=z["status"],
                fill_color=z["fill_color"],
                fill_opacity=z["fill_opacity"],
                border_color=z["border_color"],
                border_weight=z["border_weight"],
                geom=geom
            ))

        # 6. Seed Evacuation Points
        evacuation_data = [
            {
                "slug": "eva-1",
                "name": "Posko Utama Evakuasi Masjid Agung Jawa Tengah (MAJT)",
                "lat": -6.9837,
                "lng": 110.4455,
                "capacity": "1.200 jiwa",
                "supplies": "Dapur umum, medis, genset",
                "contact": "024-6725455",
                "status": "Siap Siaga"
            },
            {
                "slug": "eva-2",
                "name": "Posko Pengungsian Kantor Camat Genuk",
                "lat": -6.9628,
                "lng": 110.4705,
                "capacity": "450 jiwa",
                "supplies": "Obat-obatan dasar, perahu karet BPBD",
                "contact": "024-6582103",
                "status": "Aktif Penuh"
            },
            {
                "slug": "eva-3",
                "name": "RS Islam Sultan Agung (Layanan Gawat Darurat)",
                "lat": -6.9560,
                "lng": 110.4610,
                "capacity": "UGD 24 Jam Siaga Perahu Evakuasi",
                "supplies": "Ambulans amfibi, tabung oksigen",
                "contact": "024-6580019",
                "status": "Akses Terbatas via Truk"
            }
        ]
        for e in evacuation_data:
            geom = from_shape(Point(e["lng"], e["lat"]), srid=4326)
            db.add(EvacuationPoint(
                slug=e["slug"],
                name=e["name"],
                capacity=e["capacity"],
                supplies=e["supplies"],
                contact=e["contact"],
                status=e["status"],
                geom=geom
            ))

        # 7. Seed Alerts
        alerts_data = [
            {
                "slug": "alert-1",
                "category": "urgent",
                "title": "Peringatan Risiko Tinggi",
                "location": "Jl. Kaligawe Raya",
                "subtext": "Kedalaman air 60 cm. Tidak dapat dilalui semua jenis kendaraan.",
                "icon": "alert-triangle",
                "color": "#EF4444",
                "for_you": True,
                "action_text": "Lihat Rute Pengalihan",
                "action_route_id": "route-safe"
            },
            {
                "slug": "alert-2",
                "category": "warning",
                "title": "Waspada Banjir (Prediksi AI)",
                "location": "Kec. Genuk, Semarang",
                "subtext": "Curah hujan tinggi terdeteksi di area hulu. Waspada potensi kenaikan banjir dalam 1-2 jam ke depan.",
                "icon": "alert-circle",
                "color": "#F59E0B",
                "for_you": True,
                "action_text": "Lihat Panduan Evakuasi",
                "action_route_id": None
            },
            {
                "slug": "alert-3",
                "category": "info",
                "title": "Update Rute Navigasi",
                "location": "Rute Perjalanan Anda",
                "subtext": "Rute Anda telah otomatis disesuaikan untuk menghindari 2 titik genangan di Kaligawe.",
                "icon": "info",
                "color": "#2563EB",
                "for_you": True,
                "action_text": "Tampilkan di Peta",
                "action_route_id": "route-safe"
            },
            {
                "slug": "alert-4",
                "category": "warning",
                "title": "Peringatan Rob Pesisir BMKG",
                "location": "Kawasan Tambak Lorok & Semarang Utara",
                "subtext": "Tinggi pasang air laut diproyeksikan mencapai +110 cm pukul 14:00 - 18:00 WIB.",
                "icon": "waves",
                "color": "#F97316",
                "for_you": False,
                "action_text": "Info Detail Rob",
                "action_route_id": None
            }
        ]
        for a in alerts_data:
            db.add(Alert(**a))

        # 8. Seed Weather Cache
        db.add(WeatherForecastCache(
            city="Semarang",
            condition="Hujan Ringan",
            temp=27,
            humidity=86,
            wind_speed="14 km/jam",
            forecast_hourly=[
                {"time": "09:00", "temp": 26, "icon": "cloud-drizzle", "condition": "Gerimis"},
                {"time": "11:00", "temp": 27, "icon": "cloud-rain", "condition": "Hujan Sedang"},
                {"time": "13:00", "temp": 28, "icon": "cloud-rain", "condition": "Hujan Lebat"},
                {"time": "15:00", "temp": 27, "icon": "cloud-lightning", "condition": "Hujan Petir"},
                {"time": "17:00", "temp": 26, "icon": "cloud-rain", "condition": "Hujan Ringan"},
                {"time": "19:00", "temp": 25, "icon": "cloud", "condition": "Berawan"}
            ]
        ))

        # 9. Seed Sample Citizen Reports
        reports_data = [
            {
                "location_name": "Jl. Kaligawe Raya",
                "address": "Jl. Kaligawe Raya km 4",
                "depth_category": "40-70 cm",
                "depth_cm": 60,
                "condition": "Tidak Dapat Dilalui",
                "description": "Genangan air tinggi menutupi jalan utama depan RSI.",
                "is_verified": True,
                "verification_note": "Diverifikasi AI & Petugas Lapangan",
                "ai_confidence": 96,
                "lat": -6.9535,
                "lng": 110.4570
            },
            {
                "location_name": "Jl. Wolter Monginsidi",
                "address": "Dekat SPBU Gasem",
                "depth_category": "20-40 cm",
                "depth_cm": 25,
                "condition": "Tergenang",
                "description": "Limpasan air sungai mulai naik ke badan jalan.",
                "is_verified": True,
                "verification_note": "Diverifikasi AI (Akurasi 91%)",
                "ai_confidence": 91,
                "lat": -6.9620,
                "lng": 110.4735
            }
        ]
        for r in reports_data:
            geom = from_shape(Point(r["lng"], r["lat"]), srid=4326)
            db.add(FloodReport(
                user_id=user.id,
                location_name=r["location_name"],
                address=r["address"],
                depth_category=r["depth_category"],
                depth_cm=r["depth_cm"],
                condition=r["condition"],
                description=r["description"],
                photo_url="/assets/cctv_kaligawe.jpg",
                is_verified=r["is_verified"],
                verification_note=r["verification_note"],
                ai_confidence=r["ai_confidence"],
                geom=geom
            ))

        # 10. Seed Environmental Risk Points (PRD Bab 4 & 6.2: Infrastruktur Pengendali & Risiko Lingkungan)
        env_risks_data = [
            {
                "slug": "env-polder-tawang",
                "name": "Stasiun Pompa Polder Tawang",
                "category": "polder_pump",
                "category_label": "Stasiun Pompa Pengendali Banjir",
                "risk_level": "optimal",
                "status": "Aktif 4/4 Pompa (Kondisi Prima)",
                "capacity_or_condition": "Kapasitas debit 6,0 m³/detik",
                "description": "Menangani pembuangan air area Kota Lama dan Stasiun Kereta Api Tawang menuju Kali Semarang.",
                "icon": "pump",
                "color": "#10B981",
                "lat": -6.9688,
                "lng": 110.4285
            },
            {
                "slug": "env-polder-banger",
                "name": "Stasiun Pompa Polder Banger",
                "category": "polder_pump",
                "category_label": "Stasiun Pompa Pengendali Banjir",
                "risk_level": "optimal",
                "status": "Aktif 5/6 Pompa (1 Standby)",
                "capacity_or_condition": "Kapasitas debit 10,0 m³/detik",
                "description": "Menjaga ketinggian muka air kawasan Semarang Timur dan perkampungan sekitar Kali Banger.",
                "icon": "pump",
                "color": "#10B981",
                "lat": -6.9632,
                "lng": 110.4420
            },
            {
                "slug": "env-pompa-tenggang",
                "name": "Rumah Pompa Kali Tenggang",
                "category": "polder_pump",
                "category_label": "Stasiun Pompa Utama Muara",
                "risk_level": "medium",
                "status": "Siaga Penuh 6/6 Pompa Menyala",
                "capacity_or_condition": "Kapasitas debit 12,0 m³/detik",
                "description": "Infrastruktur vital pengendali banjir rob & limpasan kawasan Genuk, Muktiharjo, dan Kaligawe.",
                "icon": "pump",
                "color": "#F59E0B",
                "lat": -6.9455,
                "lng": 110.4615
            },
            {
                "slug": "env-pompa-waru",
                "name": "Rumah Pompa Pasar Waru",
                "category": "polder_pump",
                "category_label": "Stasiun Pompa Sekunder",
                "risk_level": "optimal",
                "status": "Aktif 2/2 Pompa",
                "capacity_or_condition": "Kapasitas debit 3,5 m³/detik",
                "description": "Mencegah genangan di area pasar dan pemukiman Gayamsari.",
                "icon": "pump",
                "color": "#10B981",
                "lat": -6.9780,
                "lng": 110.4490
            },
            {
                "slug": "env-sampah-kaligawe",
                "name": "Titik Tumpukan Sampah Jembatan Kaligawe",
                "category": "river_waste",
                "category_label": "Titik Tumpukan Sampah Sungai",
                "risk_level": "high",
                "status": "Tersumbat 55% (Aliran Melambat)",
                "capacity_or_condition": "Volume sampah ~15 m³ menghambat pilar jembatan",
                "description": "Akumulasi ranting pohon dan sampah plastik menghambat laju aliran air DAS Kali Tenggang menuju muara.",
                "icon": "trash-2",
                "color": "#EF4444",
                "lat": -6.9530,
                "lng": 110.4585
            },
            {
                "slug": "env-sampah-muara-bkt",
                "name": "Titik Penumpukan Sampah Muara BKT",
                "category": "river_waste",
                "category_label": "Titik Tumpukan Sampah Sungai",
                "risk_level": "medium",
                "status": "Tersumbat 30% di Pintu Air",
                "capacity_or_condition": "Pembersihan berkala oleh Dinas PU/BBWS",
                "description": "Muara Banjir Kanal Timur mengalami hambatan sedimentasi dan enceng gondok musiman.",
                "icon": "trash-2",
                "color": "#F59E0B",
                "lat": -6.9405,
                "lng": 110.4500
            },
            {
                "slug": "env-drainase-raden-patah",
                "name": "Saluran Drainase Kritis Jl. Raden Patah",
                "category": "drainage_choke",
                "category_label": "Saluran Drainase Kritis",
                "risk_level": "high",
                "status": "Sedimen Pasir & Tanah Capai 45 cm",
                "capacity_or_condition": "Kapasitas tampung berkurang 60%",
                "description": "Saluran sekunder mengalami sedimentasi parah, menyebabkan air mudah meluap ke badan jalan saat hujan deras.",
                "icon": "droplets",
                "color": "#EF4444",
                "lat": -6.9670,
                "lng": 110.4350
            },
            {
                "slug": "env-rob-tambak-lorok",
                "name": "Titik Kerawanan Rob Tambak Lorok",
                "category": "coastal_tide",
                "category_label": "Titik Pasang Air Laut (Rob)",
                "risk_level": "high",
                "status": "Muka Air Laut Pasang +1.15 mdpl",
                "capacity_or_condition": "Limpasan tanggul penahan laut pada pasang tinggi",
                "description": "Kawasan permukiman pesisir langsung berbatasan dengan laut Jawa, rentan limpasan pasang rob astronomis.",
                "icon": "waves",
                "color": "#F97316",
                "lat": -6.9420,
                "lng": 110.4380
            }
        ]

        for env in env_risks_data:
            geom = from_shape(Point(env["lng"], env["lat"]), srid=4326)
            db.add(EnvironmentalRiskPoint(
                slug=env["slug"],
                name=env["name"],
                category=env["category"],
                category_label=env["category_label"],
                risk_level=env["risk_level"],
                status=env["status"],
                capacity_or_condition=env["capacity_or_condition"],
                description=env["description"],
                icon=env["icon"],
                color=env["color"],
                geom=geom
            ))

        db.commit()
        print("✅ Seeding database berhasil selesai!")
        print("   - Akun Demo: andi.pratama@gmail.com / password123")
        print("   - Titik Pantau Banjir: 7 titik")
        print("   - Poligon Area Banjir: 3 zona (Kaligawe, Semarang Utara, Tugu)")
        print("   - Posko Evakuasi: 3 lokasi (MAJT, Camat Genuk, RSI Sultan Agung)")
        print("   - Faktor Risiko Lingkungan: 8 titik (Pompa Polder, Sampah Sungai, Rob)")
        print("   - Peringatan Aktif: 4 alert")
    except Exception as e:
        db.rollback()
        print(f"❌ Terjadi kesalahan saat seeding: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()


