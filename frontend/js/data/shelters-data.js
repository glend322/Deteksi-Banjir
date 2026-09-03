/**
 * SafeRoute - Evacuation Shelters & Relief Centers Data (Kota Semarang)
 */
const SAFEROUTE_SHELTERS_DATA = [
    {
        id: "shelter-majt",
        name: "Posko Utama Evakuasi Masjid Agung Jawa Tengah (MAJT)",
        location: "Jl. Gajah Raya, Gayamsari",
        capacityTotal: 1200,
        capacityOccupied: 320,
        capacityAvailable: 880,
        occupancyPercent: 26,
        status: "ready",
        statusLabel: "Siap Menampung",
        supplies: ["Dapur Umum 24 Jam", "Tim Medis & Ambulans", "Genset Darurat", "Pakaian & Selimut"],
        contact: "024-6725455",
        accessibleBy: "Semua Jenis Kendaraan"
    },
    {
        id: "shelter-camat-genuk",
        name: "Posko Pengungsian Kantor Camat Genuk",
        location: "Jl. Dongbiru No. 8, Genuk",
        capacityTotal: 450,
        capacityOccupied: 280,
        capacityAvailable: 170,
        occupancyPercent: 62,
        status: "crowded",
        statusLabel: "Hampir Penuh",
        supplies: ["2 Unit Perahu Karet BPBD", "Pos Kesehatan", "Bahan Makanan Cepat Saji"],
        contact: "024-6582103",
        accessibleBy: "Mobil SUV / Truk Tinggi"
    },
    {
        id: "shelter-rs-sultan-agung",
        name: "RS Islam Sultan Agung (Posko Medis Darurat)",
        location: "Jl. Raya Kaligawe KM 4",
        capacityTotal: 250,
        capacityOccupied: 95,
        capacityAvailable: 155,
        occupancyPercent: 38,
        status: "ready",
        statusLabel: "Khusus Penanganan Medis",
        supplies: ["UGD 24 Jam Siaga", "Ambulans Khusus Genangan", "Tabung Oksigen & Farmasi"],
        contact: "024-6580019",
        accessibleBy: "Akses Terbatas (Via Armada SAR / Truk)"
    },
    {
        id: "shelter-balai-diklat",
        name: "Balai Diklat BPSDM Jawa Tengah",
        location: "Jl. Setiabudi No. 201A, Srondol Kulon",
        capacityTotal: 600,
        capacityOccupied: 40,
        capacityAvailable: 560,
        occupancyPercent: 7,
        status: "ready",
        statusLabel: "Sangat Tersedia (Dataran Tinggi)",
        supplies: ["Kamar Tidur Asrama", "Air Bersih Melimpah", "Dapur Mandiri"],
        contact: "024-7472251",
        accessibleBy: "Bebas Banjir (Akses Mudah)"
    }
];

if (typeof window !== "undefined") {
    window.SAFEROUTE_SHELTERS_DATA = SAFEROUTE_SHELTERS_DATA;
}
