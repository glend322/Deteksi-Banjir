/**
 * SafeRoute - River Water Level (TMA) & Water Pump Station Telemetry Data
 * Data pemantauan sensor hidrologi dan pompa pengendali banjir Kota Semarang
 */
const SAFEROUTE_SENSORS_DATA = [
    {
        id: "sensor-kaligawe",
        name: "Rumah Pompa Kaligawe / Sringin",
        location: "Kec. Genuk",
        tmaCurrent: 180, // cm
        tmaWarning: 140,
        tmaDanger: 170,
        status: "danger",
        statusLabel: "Kritis (Limpasan)",
        pumpsActive: 6,
        pumpsTotal: 6,
        flowTrend: "Naik (+4 cm/jam)",
        updatedAt: "3 menit lalu"
    },
    {
        id: "sensor-kali-babon",
        name: "Sensor Aliran Kali Babon",
        location: "Perbatasan Genuk - Demak",
        tmaCurrent: 210,
        tmaWarning: 160,
        tmaDanger: 200,
        status: "danger",
        statusLabel: "Siaga II (Limpasan Hulu)",
        pumpsActive: 4,
        pumpsTotal: 4,
        flowTrend: "Naik (+8 cm/jam)",
        updatedAt: "5 menit lalu"
    },
    {
        id: "sensor-tenggang",
        name: "Rumah Pompa Kali Tenggang",
        location: "Tambakrejo, Semarang Utara",
        tmaCurrent: 165,
        tmaWarning: 130,
        tmaDanger: 180,
        status: "watch",
        statusLabel: "Waspada Rob",
        pumpsActive: 5,
        pumpsTotal: 6,
        flowTrend: "Stabil",
        updatedAt: "8 menit lalu"
    },
    {
        id: "sensor-bkb",
        name: "Pintu Air Banjir Kanal Barat",
        location: "Semarang Barat",
        tmaCurrent: 120,
        tmaWarning: 150,
        tmaDanger: 220,
        status: "safe",
        statusLabel: "Normal Lancar",
        pumpsActive: 2,
        pumpsTotal: 2,
        flowTrend: "Turun (-2 cm/jam)",
        updatedAt: "10 menit lalu"
    },
    {
        id: "sensor-pasar-waru",
        name: "Polder Pasar Waru / Kali Semarang",
        location: "Semarang Timur",
        tmaCurrent: 95,
        tmaWarning: 120,
        tmaDanger: 160,
        status: "safe",
        statusLabel: "Normal Terkendali",
        pumpsActive: 3,
        pumpsTotal: 3,
        flowTrend: "Stabil",
        updatedAt: "12 menit lalu"
    },
    {
        id: "sensor-tawang",
        name: "Polder Stasiun KA Tawang",
        location: "Semarang Tengah",
        tmaCurrent: 70,
        tmaWarning: 100,
        tmaDanger: 150,
        status: "safe",
        statusLabel: "Normal Aman",
        pumpsActive: 2,
        pumpsTotal: 2,
        flowTrend: "Stabil",
        updatedAt: "15 menit lalu"
    }
];

if (typeof window !== "undefined") {
    window.SAFEROUTE_SENSORS_DATA = SAFEROUTE_SENSORS_DATA;
}
