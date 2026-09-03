/**
 * SafeRoute - Flood Observation Points & Geospatial Data
 */
const SAFEROUTE_FLOOD_DATA = {
    riskSummary: {
        safe: { count: 12, label: "Aman", color: "#10B981", desc: "Kondisi jalan normal lancar" },
        watch: { count: 7, label: "Waspada", color: "#F59E0B", desc: "Genangan 10-20 cm, jalanan licin" },
        flooded: { count: 5, label: "Tergenang", color: "#F97316", desc: "Genangan 20-40 cm, motor rawan mogok" },
        impassable: { count: 2, label: "Tidak Dapat Dilalui", color: "#EF4444", desc: "Genangan >40 cm, jalur ditutup" }
    },

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
            recommendation: "Motor tidak disarankan lewat. Mobil ber-ground clearance tinggi harap berhati-hati.",
            vehiclesAllowed: ["Mobil SUV", "Truk"],
            cause: "Drainase tersumbat & limpasan Kali Babon"
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
    ]
};

if (typeof window !== "undefined") {
    window.SAFEROUTE_FLOOD_DATA = SAFEROUTE_FLOOD_DATA;
}
