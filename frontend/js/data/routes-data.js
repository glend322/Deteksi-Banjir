/**
 * SafeRoute - Routing Data
 */
const SAFEROUTE_ROUTES_DATA = {
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
            floodAvoided: "Menghindari 3 area banjir (Bebas Banjir 100%)",
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
};

if (typeof window !== "undefined") {
    window.SAFEROUTE_ROUTES_DATA = SAFEROUTE_ROUTES_DATA;
}
