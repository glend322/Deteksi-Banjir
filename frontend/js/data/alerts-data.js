/**
 * SafeRoute - Alerts & Early Warning Notification Data
 */
const SAFEROUTE_ALERTS_DATA = [
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
];

if (typeof window !== "undefined") {
    window.SAFEROUTE_ALERTS_DATA = SAFEROUTE_ALERTS_DATA;
}
