# PRD — AI-Based Flood Detection & Safe Route Recommendation
### Studi Kasus: Kota Semarang

**Versi:** 1.0
**Tanggal:** 2 September 2026
**Status:** Draft untuk Hackathon

---

## 1. Latar Belakang & Problem

Banjir dapat menyebabkan jalan tidak dapat dilalui, kendaraan terjebak, kemacetan, dan meningkatkan risiko keselamatan. Masalahnya, informasi mengenai jalan yang sedang tergenang sering kali tidak tersedia secara cepat dan terstruktur. Pengguna kendaraan dapat tetap melewati daerah yang sebenarnya sudah terdampak banjir karena tidak mengetahui kondisi jalan terbaru.

Kota Semarang dipilih sebagai lokasi pilot karena merupakan salah satu kota di Indonesia yang paling rawan banjir, khususnya saat musim hujan, akibat kombinasi topografi dataran rendah, drainase kota yang sering tidak memadai, serta kondisi rob (banjir air laut pasang) di beberapa wilayah pesisirnya.

Selain minimnya informasi kondisi jalan, ada dua gap tambahan yang ingin dijawab platform ini:

1. **Reaktif, bukan prediktif** — kebanyakan sistem peringatan hanya memberi tahu setelah banjir terjadi, bukan sebelum air benar-benar naik.
2. **Blind spot deteksi** — sistem berbasis kamera/CV tidak mungkin menjangkau seluruh titik kota, sehingga dibutuhkan mekanisme pelengkap dari laporan warga yang tetap dapat diverifikasi validitasnya.

---

## 2. Solusi

Platform berbasis **AI dan geospatial technology** yang mendeteksi dan memprediksi daerah terdampak banjir, menampilkannya pada peta interaktif, serta memberikan rekomendasi rute alternatif yang lebih aman berdasarkan lokasi real-time pengguna.

Sistem menggabungkan berbagai sumber data — computer vision, laporan warga (crowdsourced & terverifikasi AI), data cuaca BMKG, data historis banjir, serta faktor risiko lingkungan (drainase, tutupan lahan, sampah sungai) — untuk menghasilkan peta risiko yang akurat dan actionable.

**Konsep inti:**
> Early Warning → menjadi → Early Warning + Early Action

Bukan hanya "Daerah ini sedang banjir", tetapi:
"Daerah ini sedang banjir → jalan ini berisiko/tidak dapat dilalui → berikut rute alternatif yang menghindarinya → berikut hal yang perlu Anda lakukan."

---

## 3. Target User

| Target | Deskripsi |
|---|---|
| **Utama** | Masyarakat pengguna kendaraan (motor, mobil, transportasi umum) di Kota Semarang |
| **Sekunder** | Pemerintah daerah, BPBD Semarang, perusahaan logistik, layanan transportasi (ojek online), pengelola jalan |
| **Fokus MVP** | Pengendara di wilayah perkotaan Semarang yang rawan banjir (mis. area sekitar Kaligawe, Genuk, Semarang Utara) |

---

## 4. Data yang Dibutuhkan

**Data utama:**
- Lokasi & waktu kejadian banjir
- Status/kondisi jalan
- Kedalaman air (jika tersedia)
- Foto/video lokasi
- Koordinat GPS
- Curah hujan
- Data ketinggian air sungai/drainase (jika tersedia)
- Data elevasi/topografi
- Data jaringan jalan & lalu lintas

**Data tambahan (pengaya konteks & prediksi):**
- Laporan pengguna real-time
- Data sensor IoT (jika tersedia)
- Citra satelit
- Data cuaca real-time (BMKG)
- Informasi resmi pemerintah/lembaga terkait (BNPB, PVMBG, BPBD)
- **Data faktor risiko lingkungan**: titik penumpukan sampah di sungai, minimnya vegetasi/resapan air, kondisi drainase
- **Data historis banjir per lokasi**: frekuensi, durasi, tingkat keparahan — digunakan untuk melatih model prediksi area langganan banjir, bukan sekadar deteksi real-time

**Sumber tahap awal:** data historis banjir publik, dataset citra banjir (mis. Kaggle), data geospatial OpenStreetMap, dan data sintetis untuk melengkapi kekosongan. Data real-time (CCTV, sensor IoT) ditambahkan setelah prototype berjalan.

**Catatan privasi:** data lokasi GPS pengguna hanya digunakan untuk pencocokan area risiko & rute, dengan disclaimer eksplisit terkait penggunaan data ini kepada pengguna.

---

## 5. Cara Kerja (Alur Sistem)

```
Data Banjir (CV + Laporan Warga + Historis + Cuaca)
        ↓
   Data Processing
        ↓
Flood Detection / Risk Prediction
        ↓
   Flood Map (Fill Biru + Outline Merah)
        ↓
Route Calculation (penalti pada ruas jalan terdampak)
        ↓
Safe Route Recommendation + Personalized Alert (by GPS)
```

### 5.1 Deteksi & Klasifikasi Risiko
Setiap lokasi diberi status bertingkat:
**Normal → Waspada → Tergenang → Tidak Dapat Dilalui**

Ditambah **estimasi kedalaman air** (dalam cm) dari CV atau input laporan warga, dikategorikan menjadi level yang actionable untuk kendaraan berbeda:
- < 20 cm — aman untuk motor & mobil
- 20–40 cm — motor berisiko mogok, mobil masih relatif aman
- 40–70 cm — hanya kendaraan tinggi/mobil besar yang disarankan lewat
- \> 70 cm — tidak disarankan dilalui kendaraan apa pun

### 5.2 Computer Vision
Jika tersedia foto/video dari titik pantau, CV digunakan untuk mengidentifikasi genangan dan mengestimasi tingkat keparahannya secara otomatis.

### 5.3 Routing & Rekomendasi Rute
Ketika pengguna menentukan titik asal & tujuan (atau otomatis dari lokasi GPS saat ini), sistem memeriksa kondisi jalan pada rute tersebut. Jalan terdampak diberi penalti atau dikeluarkan dari opsi rute (algoritma Dijkstra/A* dengan kondisi banjir sebagai cost tambahan), lalu sistem merekomendasikan rute teraman — atau rute dengan banjir paling ringan jika tidak ada opsi yang sepenuhnya aman.

Contoh:
```
Dari A ke B biasanya membutuhkan 25 menit.
Jalan utama terdampak banjir (60 cm — Tidak Dapat Dilalui).
→ Rute Alternatif: +7 menit, menghindari 2 lokasi banjir.
```

### 5.4 Prediksi, Bukan Hanya Deteksi
Dengan memanfaatkan data historis + curah hujan real-time, sistem dapat memberikan **early warning prediktif** — contoh: curah hujan tinggi terdeteksi di area hulu, dan riwayat historis menunjukkan area X biasanya tergenang ±3 jam kemudian → notifikasi peringatan dikirim ke pengguna di area tersebut sebelum air benar-benar naik.

### 5.5 Freshness & Confidence Data
Setiap informasi banjir di peta disertai:
- **Waktu pembaruan terakhir** (mis. "diperbarui 10 menit lalu")
- **Confidence level** yang menurun otomatis seiring waktu jika tidak ada update baru, agar pengguna tidak mengandalkan data yang sudah usang.

---

## 6. Fitur Produk

### 6.1 Dashboard Utama
Tampilan awal berisi ringkasan kondisi banjir terkini di Semarang, cuaca hari ini, dan notifikasi penting — dikembangkan lebih dulu sebelum fitur detail lain.

### 6.2 Peta Interaktif (Fitur Inti)
- Visualisasi area banjir: **fill biru** untuk area terendam, **outline merah** untuk batas wilayah terdampak
- Filter berdasarkan kota/kecamatan/kelurahan
- **GPS tracking** pengguna (dengan permission) untuk alert yang relevan dengan lokasi
- **Rekomendasi rute aman** otomatis saat banjir terdeteksi di jalur pengguna
- **Layer area rawan banjir**: titik sampah menumpuk di sungai, minim resapan air/vegetasi, drainase buruk
- **Layer titik evakuasi & fasilitas darurat**: posko pengungsian, rumah sakit, SPBU, ATM yang masih beroperasi
- Estimasi kedalaman air per titik

### 6.3 Cuaca & Berita
- Perkiraan cuaca per jam (pagi–malam) dari BMKG
- Feed berita/informasi resmi dari BMKG, BNPB, BPBD, PVMBG

### 6.4 Forum Laporan Warga
- User dapat melaporkan kondisi banjir di lokasinya (foto, deskripsi, estimasi kedalaman)
- **AI verifikasi laporan**: cross-check dengan data curah hujan, laporan sekitar, dan/atau hasil CV sebelum ditandai "terverifikasi"
- Berfungsi sebagai pelengkap untuk area yang tidak terjangkau kamera CV
- **Trust score komunitas**: pengguna dengan riwayat laporan akurat mendapat reputasi lebih tinggi, memperkuat kredibilitas sistem verifikasi dari waktu ke waktu

### 6.5 Edukasi Kebencanaan
- Panduan pencegahan banjir
- Panduan tindakan sebelum, saat, dan sesudah banjir
- Kontak darurat cepat (BPBD, SAR, Damkar Semarang) langsung dari halaman alert

### 6.6 Fitur Pendukung Lain
- **Mode offline/low-connectivity**: cache peta & info evakuasi terakhir agar tetap bisa diakses saat koneksi lemah (PWA/service worker)
- **Riwayat pribadi**: pengguna dapat melihat riwayat banjir di lokasi yang sering dikunjungi (rumah, kantor, kos)

---

## 7. Output Sistem

- Peta lokasi & tingkat risiko banjir
- Status kondisi jalan & estimasi kedalaman air
- Waktu pembaruan data terakhir & confidence level
- Rute terdampak vs rute alternatif + estimasi waktu tempuh
- Peringatan personal saat mendekati area berisiko, lengkap dengan instruksi tindakan
- Titik evakuasi terdekat

**Contoh output:**
```
⚠️ Jalan X — Tergenang (45 cm)
Risiko: Tinggi
Update: 10 menit yang lalu (confidence: 82%)
Rekomendasi: Hindari, gunakan rute alternatif

Alternative Route: +7 menit
Flood Area Avoided: 2 lokasi

📍 Anda berada di zona risiko tinggi.
→ Segera lakukan evakuasi.
→ Titik evakuasi terdekat: 700 meter dari lokasi Anda.
```

---

## 8. Teknologi

| Layer | Teknologi |
|---|---|
| Frontend | Next.js/React (web responsif) |
| Backend | FastAPI / Node.js |
| Database | PostgreSQL + PostGIS (data geospasial) |
| AI/ML | Python, Scikit-learn/PyTorch, Computer Vision (deteksi genangan dari gambar/video) |
| Mapping & Routing | OpenStreetMap / layanan peta pihak ketiga, algoritma Dijkstra/A* dengan penalti kondisi banjir |
| Offline Support | PWA / Service Worker |

---

## 9. Scope Pengembangan

### 9.1 MVP (Prioritas Hackathon)
- [ ] Dashboard utama
- [ ] Peta interaktif dengan visualisasi area banjir (fill biru + outline merah) — boleh menggunakan data mock/dummy jika CV real-time belum siap
- [ ] Info wilayah (kota/kecamatan) + GPS tracking pengguna
- [ ] Rekomendasi rute alternatif menghindari banjir (routing API + penalti manual di area banjir)
- [ ] Estimasi kedalaman air (input manual dari laporan warga)
- [ ] Cuaca dasar dari BMKG (per jam)
- [ ] Forum laporan warga (submit + tampil di peta, tanpa AI verifikasi otomatis dulu)
- [ ] Halaman edukasi kebencanaan (statis)

### 9.2 Roadmap Selanjutnya (Pasca-MVP)
- [ ] Computer vision real-time (bisa mulai dengan model pre-trained + sample video/foto sebagai demo)
- [ ] AI verifikasi otomatis laporan warga
- [ ] Predictive alert berbasis curah hujan + data historis
- [ ] Layer area rawan banjir (sampah sungai, minim resapan air)
- [ ] Training model dari data historis banjir
- [ ] Mode offline/PWA penuh
- [ ] Trust score komunitas
- [ ] Layer titik evakuasi & fasilitas darurat
- [ ] Riwayat banjir personal per lokasi
- [ ] Integrasi sensor IoT & CCTV kota
- [ ] Ekspansi ke kota lain di luar Semarang

---

## 10. Impact & Metrik Keberhasilan

**Impact utama:**
- Mengurangi kemungkinan pengguna melewati daerah terdampak banjir → meningkatkan keselamatan
- Menghemat waktu perjalanan dengan menghindari jalan yang tidak dapat dilalui
- Membantu pemerintah/BPBD memahami persebaran banjir untuk penentuan prioritas penanganan

**Metrik keberhasilan:**
- Akurasi deteksi & prediksi banjir
- Ketepatan lokasi & waktu pembaruan informasi
- Jumlah rute yang berhasil menghindari area terdampak
- Pengurangan rata-rata waktu perjalanan dibanding rute yang terkena banjir
- Tingkat akurasi laporan warga yang terverifikasi AI
- Jumlah pengguna aktif yang menerima & menindaklanjuti alert

---

## 11. Value Proposition

Platform ini mengubah informasi banjir yang tersebar menjadi informasi geospasial yang dapat langsung digunakan untuk mengambil keputusan perjalanan — bukan sekadar "di daerah ini sedang banjir", tetapi rangkaian keputusan lengkap: **deteksi → prediksi → rute aman → tindakan yang harus dilakukan**, dipersonalisasi berdasarkan lokasi pengguna secara real-time.

Dengan menggabungkan **AI/computer vision + crowdsourced verification + geospatial data + route optimization**, sistem ini membantu masyarakat Semarang mengambil keputusan yang lebih aman dan cepat ketika terjadi banjir — sekaligus membangun infrastruktur yang dapat diperluas ke kota-kota rawan banjir lainnya di Indonesia.


## NOTE TAMBAHAN

Personalized users (dapet fitur tambahan buat yang login doang): history, saved location, alerts.