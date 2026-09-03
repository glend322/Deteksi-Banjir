/**
 * SafeRoute - Trip History & Submitted Reports Data
 */
const SAFEROUTE_HISTORY_DATA = {
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
    ],
    communityFeed: [
        {
            id: "feed-1",
            author: "Bambang Wijaya",
            location: "Jl. Kaligawe Raya KM 4",
            text: "Air semakin naik setinggi paha (sekitar 60 cm), arah Demak macet total. Kendaraan roda dua dilarang melintas sama petugas.",
            time: "8 menit lalu",
            depth: 60,
            confidence: 96,
            condition: "Tidak Dapat Dilalui"
        },
        {
            id: "feed-2",
            author: "Rina Setyowati",
            location: "Depan SPBU Wolter Monginsidi (Genuk)",
            text: "Genangan air 35 cm, sudah ada 3 motor matic mogok karena nekat menerobos. Disarankan putar lewat Bangetayu.",
            time: "16 menit lalu",
            depth: 35,
            confidence: 92,
            condition: "Tergenang"
        },
        {
            id: "feed-3",
            author: "Ahmad Fauzi (Relawan SAR)",
            location: "Simpang Gayamsari arah Majapahit",
            text: "Genangan mulai surut perlahan menjadi 12 cm, mobil kecil dan motor sudah bisa jalan pelan di lajur tengah.",
            time: "25 menit lalu",
            depth: 12,
            confidence: 98,
            condition: "Waspada"
        }
    ]
};

if (typeof window !== "undefined") {
    window.SAFEROUTE_HISTORY_DATA = SAFEROUTE_HISTORY_DATA;
}
