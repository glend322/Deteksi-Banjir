/**
 * SafeRoute - App & User Profile Data
 */
const SAFEROUTE_APP_DATA = {
    name: "SafeRoute",
    tagline: "Banjir Terpantau, Perjalanan Aman",
    subtagline: "Deteksi banjir real-time & rekomendasi rute teraman di Kota Semarang.",
    city: "Kota Semarang",
    version: "v1.2.0",
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
};

if (typeof window !== "undefined") {
    window.SAFEROUTE_APP_DATA = SAFEROUTE_APP_DATA;
}
