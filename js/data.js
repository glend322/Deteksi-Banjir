/**
 * SafeRoute - Data Store
 * Data geospasial, titik pantau, peringatan, dan rute Kota Semarang
 * Sesuai PRD Deteksi Banjir Semarang & Mockup SafeRoute
 */

const SAFEROUTE_DATA = {
    appInfo: {
        name: "SafeRoute",
        tagline: "Banjir Terpantau, Perjalanan Aman",
        subtagline: "Deteksi banjir real-time & rekomendasi rute teraman di Semarang.",
        version: "v1.0.0",
        lastUpdated: "10 menit lalu",
        user: {
            name: "Andi Pratama",
            email: "andi.pratama@gmail.com",
            avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
            vehicleType: "Mobil (City Car)",
            vehicleMaxDepth: 35, // cm
            savedLocations: [
                { id: "home", name: "Rumah", address: "Jl. Ngesrep Timur V, Banyumanik", icon: "home" },
                { id: "office", name: "Kantor", address: "Jl. Pemuda No. 142, Semarang Tengah", icon: "briefcase" },
                { id: "campus", name: "Kampus Undip", address: "Jl. Prof. Soedarto, Tembalang", icon: "graduation-cap" }
            ]
        }
    },

    weather: {
        city: "Semarang",
        condition: "Hujan Ringan",
        temp: 27,
        unit: "°C",
        humidity: 86,
        windSpeed: "14 km/jam",
        forecastHourly: [
            { time: "09:00", temp: 26, icon: "cloud-drizzle", condition: "Gerimis" },
            { time: "11:00", temp: 27, icon: "cloud-rain", condition: "Hujan Sedang" },
            { time: "13:00", temp: 28, icon: "cloud-rain", condition: "Hujan Lebat" },
            { time: "15:00", temp: 27, icon: "cloud-lightning", condition: "Hujan Petir" },
            { time: "17:00", temp: 26, icon: "cloud-rain", condition: "Hujan Ringan" },
            { time: "19:00", temp: 25, icon: "cloud", condition: "Berawan" }
        ]
    },

    riskSummary: {
        safe: { count: 12, label: "Aman", color: "#10B981", desc: "Kondisi jalan normal lancar" },
        watch: { count: 7, label: "Waspada", color: "#F59E0B", desc: "Genangan 10-20 cm, licin" },
        flooded: { count: 5, label: "Tergenang", color: "#F97316", desc: "Genangan 20-40 cm, motor rawan mogok" },
        impassable: { count: 2, label: "Tidak Dapat Dilalui", color: "#EF4444", desc: "Genangan >40 cm, ditutup total" }
    },

    // Titik pantau banjir Semarang
    floodPoints: [
        {
            id: "loc-kaligawe",
            name: "Jl. Kaligawe Raya",
            area: "Genuk, Semarang",
            lat: -6.9535,
            lng: 110.4570,
            status: "impassable",
            statusLabel: "Tidak Dapat Dilalui",
            depth: 60, // cm
            updatedAt: "10 menit lalu",
            source: "CCTV Dinas PU",
            confidence: 96,
            image: "assets/cctv_kaligawe.jpg",
            recommendation: "Hindari rute ini. Gunakan rute alternatif yang tersedia via Tol Gayamsari atau Jl. Wolter Monginsidi.",
            vehiclesAllowed: ["Hanya Truk Besar / SAR"],
            cause: "Curah hujan hulu tinggi & pasang air laut (Rob)"
        },
        {
            id: "loc-genuk",
            name: "Kecamatan Genuk (Jl. Wolter Monginsidi)",
            area: "Genuk, Semarang Timur",
            lat: -6.9620,
            lng: 110.4735,
            status: "flooded",
            statusLabel: "Tergenang",
            depth: 38,
            updatedAt: "15 menit lalu",
            source: "Laporan Warga (Terverifikasi AI)",
            confidence: 88,
            image: "assets/cctv_kaligawe.jpg",
            recommendation: "Motor tidak disarankan lewat. Mobil ber-ground clearance tinggi harap pelan-pelan.",
            vehiclesAllowed: ["Mobil SUV", "Truk"],
            cause: "Drainase tersumbat & limpasan kali Babon"
        },
        {
            id: "loc-tambakrejo",
            name: "Tambakrejo / Pelabuhan Tanjung Emas",
            area: "Semarang Utara",
            lat: -6.9450,
            lng: 110.4350,
            status: "flooded",
            statusLabel: "Tergenang",
            depth: 32,
            updatedAt: "18 menit lalu",
            source: "Sensor IoT BMKG Maritim",
            confidence: 92,
            image: "assets/cctv_kaligawe.jpg",
            recommendation: "Rob pasang laut naik. Arus air cukup deras di tepi dermaga.",
            vehiclesAllowed: ["Mobil Tinggi", "Truk"],
            cause: "Pasang Air Laut Maksimum (Rob)"
        },
        {
            id: "loc-mangkang",
            name: "Jl. Raya Mangkang - Tugu",
            area: "Tugu, Semarang Barat",
            lat: -6.9745,
            lng: 110.3320,
            status: "watch",
            statusLabel: "Waspada",
            depth: 18,
            updatedAt: "25 menit lalu",
            source: "CCTV Dishub Semarang",
            confidence: 84,
            image: "assets/cctv_kaligawe.jpg",
            recommendation: "Genangan tipis 15-18 cm di lajur kiri arah barat. Masih bisa dilalui perlahan.",
            vehiclesAllowed: ["Semua Kendaraan"],
            cause: "Limpasan air sawah & hujan lokal"
        },
        {
            id: "loc-gayamsari",
            name: "Simpang Gayamsari / Jl. Majapahit",
            area: "Gayamsari, Semarang",
            lat: -6.9940,
            lng: 110.4530,
            status: "watch",
            statusLabel: "Waspada",
            depth: 15,
            updatedAt: "30 menit lalu",
            source: "Laporan Warga",
            confidence: 79,
            image: "assets/cctv_kaligawe.jpg",
            recommendation: "Antrean padat dekat jembatan tol. Kurangi kecepatan.",
            vehiclesAllowed: ["Semua Kendaraan"],
            cause: "Drainase lambat"
        },
        {
            id: "loc-simpanglima",
            name: "Kawasan Simpang Lima & Jl. Pahlawan",
            area: "Semarang Tengah",
            lat: -6.9904,
            lng: 110.4229,
            status: "safe",
            statusLabel: "Aman",
            depth: 0,
            updatedAt: "5 menit lalu",
            source: "CCTV Smart City",
            confidence: 99,
            image: "assets/cctv_kaligawe.jpg",
            recommendation: "Jalan bebas genangan. Kondisi lalu lintas ramai lancar.",
            vehiclesAllowed: ["Semua Kendaraan"],
            cause: "Sistem pompa polder aktif normal"
        },
        {
            id: "loc-tembalang",
            name: "Kawasan Undip & Banyumanik",
            area: "Semarang Atas",
            lat: -7.0505,
            lng: 110.4410,
            status: "safe",
            statusLabel: "Aman",
            depth: 0,
            updatedAt: "8 menit lalu",
            source: "Sensor IoT",
            confidence: 100,
            recommendation: "Dataran tinggi, bebas dari risiko banjir.",
            vehiclesAllowed: ["Semua Kendaraan"],
            cause: "Elevasi >180 mdpl"
        }
    ],

    // Poligon area terdampak banjir (koordinat geo Semarang)
    // Sesuai PRD: Fill biru untuk genangan air + Outline merah untuk batas wilayah terdampak
    floodPolygons: [
        {
            id: "poly-kaligawe",
            name: "Zona Merah Kaligawe - Genuk",
            status: "impassable",
            fillColor: "#3B82F6",
            fillOpacity: 0.45,
            borderColor: "#EF4444",
            borderWeight: 3,
            coordinates: [
                [-6.945, 110.445],
                [-6.942, 110.472],
                [-6.960, 110.485],
                [-6.968, 110.468],
                [-6.958, 110.448]
            ]
        },
        {
            id: "poly-semarang-utara",
            name: "Zona Tergenang Semarang Utara & Pelabuhan",
            status: "flooded",
            fillColor: "#3B82F6",
            fillOpacity: 0.35,
            borderColor: "#EF4444",
            borderWeight: 2,
            coordinates: [
                [-6.938, 110.415],
                [-6.935, 110.445],
                [-6.955, 110.440],
                [-6.952, 110.410]
            ]
        },
        {
            id: "poly-tugu",
            name: "Zona Waspada Aliran Kali Beringin",
            status: "watch",
            fillColor: "#3B82F6",
            fillOpacity: 0.2,
            borderColor: "#F59E0B",
            borderWeight: 2,
            coordinates: [
                [-6.968, 110.320],
                [-6.965, 110.345],
                [-6.980, 110.342],
                [-6.985, 110.318]
            ]
        }
    ],

    // Titik Fasilitas Darurat & Evakuasi (PRD 6.2)
    evacuationPoints: [
        {
            id: "eva-1",
            name: "Posko Utama Evakuasi Masjid Agung Jawa Tengah (MAJT)",
            lat: -6.9837,
            lng: 110.4455,
            capacity: "1.200 jiwa",
            supplies: "Dapur umum, medis, genset",
            contact: "024-6725455",
            status: "Siap Siaga"
        },
        {
            id: "eva-2",
            name: "Posko Pengungsian Kantor Camat Genuk",
            lat: -6.9628,
            lng: 110.4705,
            capacity: "450 jiwa",
            supplies: "Obat-obatan dasar, perahu karet BPBD",
            contact: "024-6582103",
            status: "Aktif Penuh"
        },
        {
            id: "eva-3",
            name: "RS Islam Sultan Agung (Layanan Gawat Darurat)",
            lat: -6.9560,
            lng: 110.4610,
            capacity: "UGD 24 Jam Siaga Perahu Evakuasi",
            supplies: "Ambulans amfibi, tabung oksigen",
            contact: "024-6580019",
            status: "Akses Terbatas via Truk"
        }
    ],

    // Rekomendasi Rute Aman (Sesuai Mockup Layar 3 & PRD 5.3)
    routes: {
        origin: "Lokasi Saat Ini (Jl. Setiabudi)",
        destination: "Stasiun Tawang Semarang",
        options: [
            {
                id: "route-safe",
                type: "safe",
                title: "Rute Teraman",
                badge: "Terbaik",
                duration: "34 menit",
                distance: "12,4 km",
                floodAvoided: "Menghindari 3 area banjir",
                riskLevel: "Rendah",
                color: "#10B981",
                description: "Melalui Tol Tembalang - Jatingaleh - Simpang Lima - Jl. Pemuda. Jalur bebas banjir 100%.",
                path: [
                    [-7.0505, 110.4410],
                    [-7.0310, 110.4280],
                    [-7.0080, 110.4210],
                    [-6.9904, 110.4229],
                    [-6.9800, 110.4180],
                    [-6.9680, 110.4210],
                    [-6.9644, 110.4281] // Stasiun Tawang
                ]
            },
            {
                id: "route-fastest",
                type: "fastest",
                title: "Rute Tercepat",
                badge: "Risiko Sedang",
                duration: "28 menit",
                distance: "10,1 km",
                floodAvoided: "Menghindari 1 area banjir",
                riskLevel: "Sedang (Ada genangan 15 cm)",
                color: "#F59E0B",
                description: "Melalui Gayamsari. Terdapat genangan air 15 cm di dekat underpass, kendaraan rendah hati-hati.",
                path: [
                    [-7.0505, 110.4410],
                    [-7.0150, 110.4450],
                    [-6.9940, 110.4530],
                    [-6.9750, 110.4420],
                    [-6.9644, 110.4281]
                ]
            },
            {
                id: "route-alternative",
                type: "alternative",
                title: "Rute Alternatif",
                badge: "Opsi Cadangan",
                duration: "37 menit",
                distance: "13,2 km",
                floodAvoided: "Menghindari 2 area banjir",
                riskLevel: "Rendah-Sedang",
                color: "#3B82F6",
                description: "Melalui lingkar barat Arteri Yos Sudarso. Sedikit memutar tetapi kapasitas jalan lebar.",
                path: [
                    [-7.0505, 110.4410],
                    [-7.0010, 110.4050],
                    [-6.9820, 110.3950],
                    [-6.9620, 110.4020],
                    [-6.9644, 110.4281]
                ]
            }
        ]
    },

    // Peringatan Aktif (Sesuai Mockup Layar 4 & PRD 5.4, 7)
    alerts: [
        {
            id: "alert-1",
            category: "urgent",
            title: "Peringatan Risiko Tinggi",
            location: "Jl. Kaligawe Raya",
            subtext: "Kedalaman air 60 cm. Tidak dapat dilalui semua jenis kendaraan.",
            time: "10 menit lalu",
            icon: "alert-triangle",
            color: "#EF4444",
            forYou: true,
            actionText: "Lihat Rute Pengalihan",
            actionRouteId: "route-safe"
        },
        {
            id: "alert-2",
            category: "warning",
            title: "Waspada Banjir (Prediksi AI)",
            location: "Kec. Genuk, Semarang",
            subtext: "Curah hujan tinggi terdeteksi di area hulu. Waspada potensi kenaikan banjir dalam 1-2 jam ke depan.",
            time: "30 menit lalu",
            icon: "alert-circle",
            color: "#F59E0B",
            forYou: true,
            actionText: "Lihat Panduan Evakuasi",
            actionRouteId: null
        },
        {
            id: "alert-3",
            category: "info",
            title: "Update Rute Navigasi",
            location: "Rute Perjalanan Anda",
            subtext: "Rute Anda telah otomatis disesuaikan untuk menghindari 2 titik genangan di Kaligawe.",
            time: "45 menit lalu",
            icon: "info",
            color: "#2563EB",
            forYou: true,
            actionText: "Tampilkan di Peta",
            actionRouteId: "route-safe"
        },
        {
            id: "alert-4",
            category: "warning",
            title: "Peringatan Rob Pesisir BMKG",
            location: "Kawasan Tambak Lorok & Semarang Utara",
            subtext: "Tinggi pasang air laut diproyeksikan mencapai +110 cm pukul 14:00 - 18:00 WIB.",
            time: "1 jam lalu",
            icon: "waves",
            color: "#F97316",
            forYou: false,
            actionText: "Info Detail Rob",
            actionRouteId: null
        }
    ],

    // Riwayat Perjalanan & Laporan (Sesuai Mockup Layar 6)
    history: {
        trips: [
            {
                id: "trip-1",
                date: "Hari ini, 08:15",
                from: "Jl. Setiabudi",
                to: "Stasiun Tawang",
                duration: "34 menit",
                distance: "12,4 km",
                routeType: "Rute Teraman",
                status: "Berhasil Menghindar Banjir"
            },
            {
                id: "trip-2",
                date: "Kemarin, 17:40",
                from: "Undip Tembalang",
                to: "Genuk",
                duration: "29 menit",
                distance: "9,8 km",
                routeType: "Rute Tercepat",
                status: "Melalui Genangan Rendah"
            },
            {
                id: "trip-3",
                date: "2 Sep 2026, 07:30",
                from: "Banyumanik",
                to: "Tugu",
                duration: "32 menit",
                distance: "11,3 km",
                routeType: "Rute Alternatif",
                status: "Lancar Terkendali"
            }
        ],
        reports: [
            {
                id: "rep-1",
                date: "2 Sep 2026, 06:45",
                location: "Jl. Kaligawe Raya",
                address: "Jl. Kaligawe Raya km 4",
                depth: "60 cm",
                status: "Tidak Dapat Dilalui",
                statusColor: "#EF4444",
                verified: true,
                verificationNote: "Diverifikasi AI & Petugas Lapangan"
            },
            {
                id: "rep-2",
                date: "1 Sep 2026, 16:10",
                location: "Jl. Wolter Monginsidi",
                address: "Dekat SPBU Gasem",
                depth: "25 cm",
                status: "Tergenang",
                statusColor: "#F97316",
                verified: true,
                verificationNote: "Diverifikasi AI (Akurasi 91%)"
            }
        ]
    },

    // Kontak Darurat Kota Semarang (PRD 6.5)
    emergencyContacts: [
        { name: "Panggilan Darurat Terpadu Kota Semarang", number: "112", desc: "Bebas Pulsa 24 Jam (Ambulans, BPBD, Polisi, Damkar)" },
        { name: "Pusdalops BPBD Kota Semarang", number: "024-3580007", desc: "Evakuasi banjir, logistik pengungsian, perahu karet" },
        { name: "Kantor SAR / Basarnas Semarang", number: "024-7607777", desc: "Penyelamatan darurat & evakuasi air deras" },
        { name: "Dinas Pemadam Kebakaran Semarang", number: "113", desc: "Pompa penyedot darurat & pembersihan material" },
        { name: "Palang Merah Indonesia (PMI) Semarang", number: "024-3541237", desc: "Bantuan medis pertama & ambulans" }
    ],

    // Panduan Edukasi Kebencanaan (PRD 6.5)
    floodGuide: {
        before: [
            "Pantau terus peta SafeRoute dan perkiraan cuaca BMKG Kota Semarang.",
            "Simpan dokumen penting dan barang berharga di tempat yang tinggi atau plastik kedap air.",
            "Ketahui letak MCB listrik dan matikan bila air mulai memasuki pemukiman.",
            "Cek kendaraan: pastikan rem, filter udara, dan knalpot dalam kondisi optimal."
        ],
        during: [
            "JANGAN memaksakan menerobos banjir bila kedalaman melebihi batas ground clearance kendaraan (>30 cm untuk motor/sedan).",
            "Bila kendaraan mogok di tengah banjir, segera tinggalkan kendaraan dan berjalan ke tempat yang lebih tinggi.",
            "Hindari menyentuh tiang listrik, kabel jatuh, atau papan reklame berlistrik.",
            "Buka rute SafeRoute untuk menemukan titik posko evakuasi terdekat yang aktif."
        ],
        after: [
            "Jangan langsung menyalakan mesin kendaraan yang sempat terendam sebelum oli dan kelistrikan dicek mekanik.",
            "Gunakan alas kaki anti robek saat membersihkan sisa lumpur banjir untuk menghindari infeksi Leptospirosis.",
            "Laporkan kondisi terkini jalan Anda melalui fitur Laporkan Banjir SafeRoute guna membantu warga lain."
        ],
        vehicleThresholds: [
            { vehicle: "Motor Bebek / Matic", maxDepth: "20 cm", advice: "Air setinggi knalpot / filter udara, jangan dipaksakan." },
            { vehicle: "Mobil Sedan / City Car", maxDepth: "30 cm", advice: "Batas bawah bumper; air bisa masuk ke ruang mesin." },
            { vehicle: "Mobil SUV / MPV Tinggi", maxDepth: "50 cm", advice: "Jaga putaran gas stabil pada gigi rendah, jangan lepas pedal gas mendadak." },
            { vehicle: "Truk / Kendaraan Khusus", maxDepth: "70 cm", advice: "Tetap waspada terhadap lubang jalan tak terlihat di bawah air." }
        ]
    }
};

if (typeof window !== "undefined") {
    window.SAFEROUTE_DATA = SAFEROUTE_DATA;
}
