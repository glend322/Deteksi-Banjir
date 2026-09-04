# Modeling Team — PRD

**Project:** SafeRoute — AI-Based Flood Detection & Safe Route Recommendation
**Focus:** Kota Semarang
**Date:** 4 September 2026
**Version:** 2.0

---

## 1. Hard Constraints (Rules)

### Rule 1 — Folder Isolation
Semua kode modeling, model, dataset, config, dan documentation HARUS berada di dalam `modeling/`. Dilarang mengedit:
- `main.html`, `css/`, `js/`, `assets/`
- `PRD_Deteksi_Banjir_Semarang.md`
- `backend/` (kecuali read untuk memahami API contract)
- `.git/` config

**Exception:** Boleh membaca `js/data.js` untuk memahami output format yang diharapkan frontend.

### Rule 2 — Output Contract
Semua output harus kompatibel dengan `SAFEROUTE_DATA` di `js/data.js`:
- Flood points: `lat`, `lng`, `depth`, `status`, `confidence`, `area`, `source`
- Routes: `path` sebagai `[[lat, lng], ...]`, `color`, `riskLevel`, `duration`, `distance`
- Status enum: `"safe"` | `"watch"` | `"flooded"` | `"impassable"`

### Rule 3 — No Secrets
API keys dimuat dari `.env`. Jangan commit secrets.

### Rule 4 — Reproducibility
Setiap model harus punya: `requirements.txt`, README, saved checkpoints, pinned random seeds.

### Rule 5 — Data Provenance
Semua dataset didokumentasi di `data/README.md` dengan: source, license, size, date range, preprocessing.

### Rule 6 — Scraping Ethics
Rate-limit max 1 req/det per domain. Cache hasil scrape. Document semua sumber.

---

## 2. Overview — 2 Core Capabilities

Modeling memiliki **2 capability utama** + modul pendukung:

| # | Capability | Deskripsi |
|---|---|---|
| **1** | **Safe Route Engine** | Kalkulasi rute aman berdasarkan lokasi real-time user, dengan penalty untuk jalan terdampak banjir + rekomendasi evakuasi terdekat |
| **2** | **CCTV Flood Detection Pipeline** | Pipeline end-to-end: CCTV Semarang → CV detection → verifikasi false positive → klasifikasi tingkat banjir (dangkal/sedang/dalam) → output notifikasi |

**Modul Pendukung:**
- Data Scraping Pipeline (BMKG, OSM, Kaggle)
- Area Mapping (koordinat → nama daerah)
- FastAPI endpoints

---

## 3. Capability 1 — Safe Route Engine

### 3.1 Purpose
Memberikan rekomendasi rute aman kepada pengguna saat banjir terdeteksi. Sistem menghitung ulang rute dengan mempertimbangkan kondisi jalan (banjir) secara real-time, mirip cara kerja Google Maps tetapi dengan layer data banjir.

### 3.2 Alur Kerja

```
Lokasi User (GPS lat/lng)
        ↓
Ambil Titik Banjir Aktif (dari database/CCTV)
        ↓
Label Status Jalan per Ruas:
  - green (#10B981)  = aman
  - yellow (#F59E0B) = dangkal (<20cm)
  - orange (#F97316) = sedang (20-40cm)
  - red (#EF4444)    = dalam (>40cm, tidak dapat dilalui)
        ↓
Hitung 3 Opsi Rute (Dijkstra/A* dengan flood penalty):
  1. Rute Teraman   (hijau, 0% banjir)
  2. Rute Tercepat   (kuning/orange, ada genangan ringan)
  3. Rute Alternatif (biru, sedikit memutar tapi aman)
        ↓
Cari Titik Evakuasi Terdekat dari lokasi user
        ↓
Output:
  - 3 opsi rute dengan path, warna, durasi, jarak
  - Titik evakuasi terdekat
  - Notifikasi jika user mendekati zona berbahaya
```

### 3.3 Input

```json
{
  "origin": {
    "lat": -7.0505,
    "lng": 110.4410,
    "name": "Lokasi Saat Ini"
  },
  "destination": {
    "lat": -6.9644,
    "lng": 110.4281,
    "name": "Stasiun Tawang"
  },
  "vehicle_max_depth_cm": 30
}
```

### 3.4 Output

```json
{
  "origin": "Lokasi Saat Ini",
  "destination": "Stasiun Tawang",
  "flood_zones_active": 3,
  "options": [
    {
      "id": "route-safe",
      "type": "safe",
      "title": "Rute Teraman",
      "badge": "Terbaik",
      "duration": "34 menit",
      "distance": "12.4 km",
      "flood_avoided": "Menghindari 3 area banjir",
      "risk_level": "Rendah",
      "color": "#10B981",
      "road_labels": [
        {"segment": "Tembalang - Jatingaleh", "status": "safe", "color": "#10B981"},
        {"segment": "Jatingaleh - Simpang Lima", "status": "safe", "color": "#10B981"}
      ],
      "path": [
        [-7.0505, 110.4410],
        [-7.0310, 110.4280],
        [-6.9904, 110.4229],
        [-6.9644, 110.4281]
      ]
    },
    {
      "id": "route-fastest",
      "type": "fastest",
      "title": "Rute Tercepat",
      "badge": "Risiko Sedang",
      "duration": "28 menit",
      "distance": "10.1 km",
      "flood_avoided": "Menghindari 1 area banjir",
      "risk_level": "Sedang",
      "color": "#F59E0B",
      "road_labels": [
        {"segment": "Gayamsari - Underpass", "status": "dangkal", "color": "#F59E0B", "depth_cm": 15},
        {"segment": "Underpass - Stasiun Tawang", "status": "safe", "color": "#10B981"}
      ],
      "path": [
        [-7.0505, 110.4410],
        [-6.9940, 110.4530],
        [-6.9644, 110.4281]
      ]
    }
  ],
  "nearest_evacuation": {
    "id": "eva-1",
    "name": "Posko Utama MAJT",
    "lat": -6.9837,
    "lng": 110.4455,
    "distance_km": 2.3,
    "duration_walk": "28 menit"
  }
}
```

### 3.5 Routing Algorithm

**Algoritma:** A* (A-star) dengan modified cost function

```
cost(u, v) = base_distance(u, v) * flood_penalty(status(u, v))
```

**Flood Penalty Table:**

| Status Jalan | Penalty Multiplier | Artinya |
|---|---|---|
| safe | 1.0 | Tidak ada penalti |
| dangkal (<20cm) | 1.5 | Sedikit lebih lambat |
| sedang (20-40cm) | 3.0 | Motor tidak bisa lewat, mobil pelan |
| dalam (>40cm) | INF | Tidak dapat dilalui, dikecualikan dari graph |

**Vehicle Filter:**
Jika `vehicle_max_depth_cm` ditentukan, jalan dengan depth > vehicle_max akan diberi penalty INF.

### 3.6 Road Labeling (Visual Map)

Setiap segmen jalan pada rute dilabeli warna tebal:
- **Green thick line** (`#10B981`, weight 5) = aman
- **Yellow thick line** (`#F59E0B`, weight 5) = dangkal
- **Orange thick line** (`#F97316`, weight 5) = sedang
- **Red thick line** (`#EF4444`, weight 5) = dalam / tertutup

Data `road_labels` dikirim ke frontend untuk rendering garis tebal di peta.

### 3.7 Evacuation Finder

**Input:** User lat/lng + daftar titik evakuasi
**Output:** Titik evakuasi terdekat + estimasi jarak/waktu

Algoritma: Haversine distance, filter yang masih aktif (`status == "Siap Siaga"` atau `"Aktif"`).

### 3.8 Deliverables

```
modeling/
├── route_engine.py           # A* routing dengan flood penalty
├── evacuation_finder.py      # Cari titik evakuasi terdekat
├── area_mapping.py           # Reverse geocode: lat/lng → nama kecamatan/kelurahan
```

---

## 4. Capability 2 — CCTV Flood Detection Pipeline

### 4.1 Purpose
Mendeteksi banjir secara otomatis dari CCTV Kota Semarang, memverifikasi apakah benar banjir atau false positive, mengklasifikasikan tingkat keparahan, lalu menghasilkan notifikasi.

### 4.2 Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    CCTV FLOOD DETECTION PIPELINE             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [1] CCTV Client                                           │
│      Source: pantausemar.semarangkota.go.id                 │
│      Categories: rawan_genangan, sungai, pompa_air          │
│      Output: frame (JPEG bytes) + metadata (nama, lat/lng)  │
│                          ↓                                  │
│  [2] CV Flood Detection                                     │
│      Model: CNN (ResNet50 / MobileNetV3)                    │
│      Input: image frame                                     │
│      Output: flood_detected (bool), depth_cm (float),       │
│              confidence (float), class probabilities        │
│                          ↓                                  │
│  [3] Verifier (False Positive Filter)                       │
│      Checks:                                               │
│        - Apakah gambar terlalu gelap/terang?                │
│        - Apakah ada tekstur air yang konsisten?             │
│        - Apakah confidence model cukup tinggi?              │
│        - Historical: apakah lokasi ini sering banjir?       │
│      Output: is_genuine_flood (bool), reasons (list)        │
│                          ↓                                  │
│  [4] Classifier (Klasifikasi Tingkat Banjir)                │
│      Input: depth_cm dari CV model                          │
│      Output:                                                │
│        - dangkal  : depth < 20 cm                           │
│        - sedang   : depth 20-40 cm                          │
│        - dalam    : depth > 40 cm                           │
│                          ↓                                  │
│  [5] Output / Notifikasi                                    │
│      Format: "Daerah {nama_daerah} banjir di tingkat        │
│               {dangkal/sedang/dalam}"                       │
│      + Simpan ke backend database                           │
│      + Kirim alert ke frontend                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Stage 1 — CCTV Client

**Source:** Pantau Semarang (https://pantausemar.semarangkota.go.id/)

**Kategori CCTV:**
| Kategori | UUID | Prioritas |
|---|---|---|
| rawan_genangan | `df69dbea-87c9-4d79-9ddc-f388c33f2dc9` | Tinggi |
| sungai | `194fd5d9-098f-4dbe-93da-8288c6761bf0` | Tinggi |
| pompa_air | `5b5b7e51-3a2e-446f-8fae-50d8e9e7196d` | Tinggi |

**Cara Kerja:**
1. Scrape HTML dari Pantau Semar → ekstrak JSON `var cctvs = [...]`
2. Filter kategori flood-related
3. Extract frame dari HLS stream (`.m3u8`) menggunakan ffmpeg
4. Output: JPEG bytes + camera metadata

**Output per camera:**
```python
@dataclass
class CCTVFrame:
    camera_id: int
    name: str           # nama lokasi CCTV
    lat: float
    lng: float
    stream_url: str
    frame_bytes: bytes   # JPEG
    timestamp: float
    category: str        # rawan_genangan / sungai / pompa_air
```

### 4.4 Stage 2 — CV Flood Detection Model

**Architecture:**
- Base: Pre-trained CNN backbone (pilihan: ResNet50, EfficientNet-B0, MobileNetV3-Small)
- Dual-head output:
  - **Classification head**: 2 kelas (flood / no_flood)
  - **Regression head**: estimasi kedalaman air (cm)

**Input:** Image 224x224 RGB
**Output:**
```json
{
  "flood_detected": true,
  "depth_estimate_cm": 35.2,
  "confidence": 0.89,
  "probabilities": {"no_flood": 0.11, "flood": 0.89}
}
```

**Training Data:**
- Kaggle flood detection datasets
- CCTV snapshots dari Pantau Semarang (scraped)
- Augmented data: water-color overlay pada gambar jalan normal

**Target Metrics:**
- Accuracy: > 85%
- Depth estimation MAE: < 10 cm

### 4.5 Stage 3 — Verifier (False Positive Filter)

**Purpose:** Memastikan bahwa deteksi banjir dari CV model benar-benar banjir, bukan误判 (misal: bayangan, genangan kecil, gambar gelap).

**Rule-based Checks:**

| Rule | Condition | Effect |
|---|---|---|
| brightness_check | Frame terlalu gelap (<30) atau terang (>240) | Flag suspicious |
| water_texture | Rasio piksel biru/hijau terlalu rendah | Flag suspicious |
| confidence_gate | CV confidence < 0.6 | Reject detection |
| depth_gate | depth_cm < 5 | Reject (terlalu kecil) |
| location_history | Lokasi ini punya riwayat banjir | Boost confidence |
| temporal_consistency | Deteksi serupa dalam 5 menit terakhir di camera yang sama | Boost confidence |

**Output:**
```python
@dataclass
class VerificationResult:
    is_genuine_flood: bool
    confidence_modifier: float  # -0.2 s/d +0.2
    reasons: list[str]          # ["low_brightness", "historical_flood_hotspot"]
```

### 4.6 Stage 4 — Classifier (Klasifikasi Tingkat Banjir)

**Input:** `depth_cm` dari CV model + `is_genuine_flood` dari verifier

**Klasifikasi:**

| Kategori | Depth Range | Warna | Artinya |
|---|---|---|---|
| **dangkal** | < 20 cm | `#F59E0B` (kuning) | Air menggenang tipis, masih bisa dilalui semua kendaraan dengan hati-hati |
| **sedang** | 20-40 cm | `#F97316` (orange) | Motor berisiko mogok, mobil ber-ground clearance tinggi masih bisa lewat |
| **dalam** | > 40 cm | `#EF4444` (merah) | Tidak disarankan dilalui kendaraan apapun, jalur tertutup |

### 4.7 Stage 5 — Output Notifikasi

**Format Notifikasi:**
```
Daerah {nama_daerah} banjir di tingkat {dangkal|sedang|dalam}
```

**Contoh:**
```
Daerah Kaligawe banjir di tingkat dalam
Daerah Genuk banjir di tingkat sedang
Daerah Mangkang banjir di tingkat dangkal
```

**Full Detection Result:**
```python
@dataclass
class FloodDetection:
    camera_id: int
    camera_name: str
    lat: float
    lng: float
    area_name: str           # dari area_mapping (kecamatan/kelurahan)
    is_flood: bool
    depth_cm: float
    classification: str      # "dangkal" | "sedang" | "dalam"
    confidence: float
    is_false_positive: bool
    notification: str        # "Daerah X banjir di tingkat Y"
    timestamp: float
```

**Delivery:**
1. Simpan ke backend database (`POST /api/internal/ai/predictions`)
2. Tampilkan di peta interaktif (flood point baru)
3. Kirim push notification ke user di area sekitar

### 4.8 Continuous Monitoring

Worker berjalan secara periodik:
- Default interval: 60 detik per scan cycle
- Scan semua CCTV dalam kategori flood-related
- Cooldown per camera: 15 menit (hindari spam notifikasi yang sama)
- Logging semua deteksi ke file

### 4.9 Deliverables

```
modeling/
├── cctv_client.py            # Scraping CCTV + extract frame dari HLS
├── cv_model.py               # Arsitektur CNN flood detection
├── verifier.py               # False positive filter
├── classifier.py             # Klasifikasi: dangkal/sedang/dalam
├── detector.py               # Pipeline utama: CCTV → CV → Verify → Classify → Output
├── area_mapping.py           # Reverse geocode: lat/lng → nama daerah
├── worker.py                 # Background worker untuk continuous monitoring
├── checkpoints/
│   └── best.pt              # Saved model weights
```

---

## 5. Modul Pendukung

### 5.1 Data Scraping Pipeline

| Source | Data Type | Purpose |
|---|---|---|
| BMKG (cuaca.bmkg.go.id) | Curah hujan real-time & historis | Input prediksi banjir |
| OpenStreetMap (Overpass API) | Drainase, jalan, sungai, land use | Feature engineering + routing graph |
| Kaggle | Dataset citra banjir | Training CV model |
| Pantau Semarang | CCTV snapshots real-time | Input CV classifier |

**Deliverables:**
```
modeling/data_scraper/
├── bmkg_scraper.py
├── osm_scraper.py
├── kaggle_downloader.py
├── utils.py                  # rate limiter, cache, retry
└── config.yaml
```

### 5.2 FastAPI Endpoints

Exposed untuk integrasi dengan backend utama.

**Endpoints:**
```
POST /api/classify-image
  → Input: image file
  → Output: { flood_detected, classification, depth_cm, confidence }

POST /api/scan-cctv
  → Input: { categories, camera_ids }
  → Output: list of detections dari semua CCTV

POST /api/calculate-route
  → Input: { origin, destination, vehicle_max_depth }
  → Output: 3 route options + nearest evacuation

GET  /api/flood-zones
  → Output: semua titik banjir aktif + status

GET  /health
  → Output: { status, version }
```

**Deliverables:**
```
modeling/api/
├── main.py
├── schemas.py
├── dependencies.py
```

### 5.3 Data Directory

```
modeling/data/
├── README.md                 # Dokumentasi semua dataset
├── raw/                      # Data mentah dari scraping
├── processed/                # Data yang sudah dibersihkan
└── sample/                   # Sample kecil untuk testing cepat
```

---

## 6. Output Contract — Interface dengan Frontend

### 6.1 Flood Points (untuk peta)

Harus kompatibel dengan `SAFEROUTE_DATA.floodPoints` di `js/data.js`:

```json
{
  "id": "loc-cctv-123",
  "name": "Jl. Kaligawe Raya",
  "area": "Genuk, Semarang",
  "lat": -6.9535,
  "lng": 110.4570,
  "status": "impassable",
  "statusLabel": "Tidak Dapat Dilalui",
  "depth": 60,
  "updatedAt": "10 menit lalu",
  "source": "CCTV Pantau Semarang",
  "confidence": 96,
  "recommendation": "Hindari rute ini.",
  "vehiclesAllowed": ["Hanya Truk Besar / SAR"],
  "cause": "Deteksi CCTV AI Real-Time"
}
```

**Mapping classification → status:**

| Classification | status (frontend) | statusLabel |
|---|---|---|
| dangkal | `"watch"` | `"Waspada"` |
| sedang | `"flooded"` | `"Tergenang"` |
| dalam | `"impassable"` | `"Tidak Dapat Dilalui"` |

### 6.2 Routes (untuk rute navigasi)

Harus kompatibel dengan `SAFEROUTE_DATA.routes` di `js/data.js`:

```json
{
  "id": "route-safe",
  "type": "safe",
  "title": "Rute Teraman",
  "badge": "Terbaik",
  "duration": "34 menit",
  "distance": "12,4 km",
  "floodAvoided": "Menghindari 3 area banjir",
  "riskLevel": "Rendah",
  "color": "#10B981",
  "description": "Jalur bebas banjir 100%.",
  "path": [[-7.0505, 110.4410], [-6.9644, 110.4281]]
}
```

### 6.3 Notifikasi Output

Format notifikasi dari pipeline CCTV:

```
Daerah Kaligawe banjir di tingkat dalam
```

Disimpan ke database dengan field:
- `source_name`: "CCTV Pantau Semarang"
- `location_name`: nama camera
- `area`: nama kecamatan/kelurahan
- `lat`, `lng`
- `estimated_depth_cm`
- `classification`: dangkal/sedang/dalam
- `confidence`
- `alert_needed`: true
- `cause`: "Deteksi CCTV AI Real-Time"

---

## 7. Target Directory Structure (Full)

```
modeling/
├── MODELING_PRD.md               # Dokumen ini
├── README.md                     # Setup & usage instructions
├── requirements.txt              # Python dependencies
├── .env.example                  # Template API keys
├── .gitignore                    # Ignore .env, __pycache__, checkpoints
│
├── cctv_client.py                # Stage 1: Scraping CCTV + extract frame
├── cv_model.py                   # Stage 2: CNN flood detection architecture
├── verifier.py                   # Stage 3: False positive filter
├── classifier.py                 # Stage 4: Klasifikasi dangkal/sedang/dalam
├── detector.py                   # Stage 5: Pipeline utama (orchestrator)
├── area_mapping.py               # Reverse geocode → nama daerah
├── route_engine.py               # Safe route: A* + flood penalty
├── evacuation_finder.py          # Titik evakuasi terdekat
├── worker.py                     # Background worker (continuous monitoring)
│
├── api/
│   ├── main.py                   # FastAPI app
│   ├── schemas.py                # Pydantic models
│   └── dependencies.py           # Model loading, shared state
│
├── data_scraper/
│   ├── bmkg_scraper.py
│   ├── osm_scraper.py
│   ├── kaggle_downloader.py
│   ├── utils.py
│   └── config.yaml
│
├── checkpoints/
│   └── best.pt                   # CV model weights
│
├── data/
│   ├── README.md
│   ├── raw/
│   ├── processed/
│   └── sample/
│
└── notebooks/
    └── 01_exploration.ipynb
```

---

## 8. Execution Phases

### Phase 1 — Data & Scraping (Day 1)
- [ ] Set up `requirements.txt` dan `.env.example`
- [ ] Build `cctv_client.py` — scrape Pantau Semar, extract frame dari HLS
- [ ] Build `area_mapping.py` — reverse geocode lat/lng → nama kecamatan
- [ ] Build `data_scraper/bmkg_scraper.py` — curah hujan BMKG
- [ ] Build `data_scraper/kaggle_downloader.py` — download flood image dataset
- [ ] Download flood image dataset dari Kaggle
- [ ] Document semua sumber di `data/README.md`

### Phase 2 — CV Model (Day 2-3)
- [ ] Build `cv_model.py` — arsitektur CNN (MobileNetV3 atau ResNet50)
- [ ] Build training pipeline — train di flood image dataset
- [ ] Target: accuracy > 85%, depth MAE < 10cm
- [ ] Save checkpoint ke `checkpoints/best.pt`
- [ ] Build `verifier.py` — false positive filter (rule-based)
- [ ] Build `classifier.py` — mapping depth → dangkal/sedang/dalam

### Phase 3 — Pipeline & Route Engine (Day 3-4)
- [ ] Build `detector.py` — orchestrate CCTV → CV → Verify → Classify → Output
- [ ] Build `route_engine.py` — A* routing dengan flood penalty
- [ ] Build `evacuation_finder.py` — cari evakuasi terdekat
- [ ] Test pipeline end-to-end dengan sample CCTV

### Phase 4 — API & Worker (Day 4-5)
- [ ] Build `api/main.py` — FastAPI endpoints
- [ ] Build `api/schemas.py` — Pydantic models sesuai output contract
- [ ] Build `worker.py` — background monitoring
- [ ] Test API locally

### Phase 5 — Integration & Demo (Day 5)
- [ ] End-to-end demo: CCTV frame → CV → notifikasi "Daerah X banjir di tingkat Y"
- [ ] End-to-end demo: user GPS → 3 rute opsi + evakuasi terdekat
- [ ] Output format compatible dengan `SAFEROUTE_DATA`
- [ ] Write README

---

## 9. Success Metrics

| Metric | Target |
|---|---|
| CV classifier accuracy | > 85% |
| CV depth estimation MAE | < 10 cm |
| False positive filter precision | > 90% |
| API response time | < 500ms |
| CCTV scan per cycle | < 30 detik untuk semua camera |
| Route calculation | < 200ms |
| Notifikasi format | "Daerah X banjir di tingkat Y" sesuai spec |
