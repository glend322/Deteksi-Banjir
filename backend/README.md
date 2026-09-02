# SafeRoute Backend API (FastAPI + PostgreSQL/PostGIS)

Backend RESTful API dan sistem geospasial untuk deteksi banjir & rekomendasi rute aman Kota Semarang sesuai PRD.

---

## 🛠️ Persyaratan Sistem
1. Python 3.10+
2. Docker & Docker Compose (untuk PostgreSQL + PostGIS)

---

## 🚀 Cara Menjalankan

### 1. Jalankan Database PostGIS (Docker)
```bash
cd backend
docker compose up -d
```

### 2. Setup Virtual Environment Python & Install Dependensi
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Inisialisasi & Seeding Database Semarang
Jalankan script untuk mengimpor titik pantau, poligon batas banjir, posko evakuasi, dan akun demo:
```bash
python -m app.seed
```

### 4. Jalankan Server FastAPI
```bash
uvicorn app.main:app --reload --port 8000
```

---

## 📖 Dokumentasi API Interaktif (Swagger UI)
Setelah server berjalan, buka di browser:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🔑 Akun Demo Default
- **Email:** `andi.pratama@gmail.com`
- **Password:** `password123`

---

## 📌 Endpoint API Utama

| Kategori | Method & Endpoint | Deskripsi |
|---|---|---|
| **Auth** | `POST /api/auth/register` | Mendaftar akun warga baru |
| | `POST /api/auth/login` | Login & mendapatkan JWT Bearer Token |
| **Profil User** | `GET /api/users/me` | Mengambil profil user & spesifikasi kendaraan |
| | `PUT /api/users/me` | Memperbarui tipe kendaraan & toleransi genangan |
| | `GET /api/users/saved-locations` | Mengambil alamat favorit (Rumah, Kantor, Kampus) |
| **Data Banjir (GIS)** | `GET /api/flood/points` | Mengambil semua titik pantau banjir (filter: safe, watch, flooded, impassable) |
| | `GET /api/flood/polygons` | Mengambil GeoJSON batas area banjir (Fill Biru + Outline Merah) |
| | `GET /api/flood/summary` | Ringkasan jumlah titik per tingkat risiko |
| **Rute Aman** | `POST /api/routes/calculate` | Kalkulasi 3 rekomendasi rute (Teraman, Tercepat, Alternatif) |
| **Evakuasi** | `GET /api/evacuations/nearest` | Mencari posko evakuasi terdekat berdasarkan GPS (`ST_Distance`) |
| **Laporan Warga** | `POST /api/reports` | Mengirim laporan genangan air (mendukung upload foto) |
| | `GET /api/reports` | Melihat laporan warga terbaru |
| **Cuaca & Alert** | `GET /api/weather/current` | Perkiraan cuaca BMKG per jam |
| | `GET /api/weather/alerts` | Daftar peringatan darurat aktif |

