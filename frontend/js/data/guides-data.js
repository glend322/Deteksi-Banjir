/**
 * SafeRoute - Disaster Preparedness Guidelines & Vehicle Water Thresholds Data
 */
const SAFEROUTE_GUIDES_DATA = {
    before: [
        "Pantau terus peta SafeRoute dan perkiraan cuaca BMKG Kota Semarang sebelum bepergian.",
        "Simpan dokumen penting dan barang berharga di tempat yang tinggi atau wadah kedap air.",
        "Ketahui letak saklar utama MCB listrik dan matikan bila genangan mulai masuk pemukiman.",
        "Cek kendaraan: pastikan sistem pengereman, filter udara, dan ketinggian knalpot dalam kondisi prima."
    ],
    during: [
        "JANGAN memaksakan menerobos banjir bila kedalaman melebihi batas ground clearance kendaraan (>25-30 cm).",
        "Bila mesin kendaraan mati mendadak di tengah banjir, JANGAN starter ulang. Segera keluar dan dorong ke tepi.",
        "Hindari menyentuh tiang listrik, reklame bertegangan, atau pohon besar saat melintasi arus air deras.",
        "Buka fitur Rute Aman SafeRoute untuk memandu arah menuju posko evakuasi darurat terdekat."
    ],
    after: [
        "Jangan langsung menyalakan mesin kendaraan yang sempat terendam sebelum oli dan kelistrikan dicek teknisi.",
        "Gunakan sepatu boots anti robek saat membersihkan endapan lumpur untuk mencegah Leptospirosis.",
        "Laporkan kondisi genangan terbaru di sekitar Anda melalui menu Laporkan Banjir SafeRoute guna membantu warga lain."
    ],
    vehicleThresholds: [
        {
            vehicle: "Motor Bebek / Matic",
            type: "motor",
            icon: "🛵",
            maxDepth: "20 cm",
            badgeClass: "low",
            advice: "Batas setinggi velg/knalpot. Rawan masuk ke box filter udara CVT dan mesin mati mendadak."
        },
        {
            vehicle: "Mobil Sedan / City Car",
            type: "sedan",
            icon: "🚗",
            maxDepth: "30 cm",
            badgeClass: "medium",
            advice: "Batas bawah bumper depan. Berisiko air terhisap intake udara (water hammer)."
        },
        {
            vehicle: "Mobil SUV / MPV Tinggi",
            type: "suv",
            icon: "🚙",
            maxDepth: "50 cm",
            badgeClass: "high",
            advice: "Gunakan gigi rendah (L/1), pertahankan rpm gas stabil, dan hindari gelombang haluan dari truk."
        },
        {
            vehicle: "Truk & Armada SAR",
            type: "truck",
            icon: "🚛",
            maxDepth: "70 cm",
            badgeClass: "special",
            advice: "Aman melewati genangan dalam, tetap waspada terhadap lubang jalan tersembunyi di bawah air."
        }
    ]
};

if (typeof window !== "undefined") {
    window.SAFEROUTE_GUIDES_DATA = SAFEROUTE_GUIDES_DATA;
}
