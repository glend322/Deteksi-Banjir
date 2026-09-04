/**
 * SafeRoute - Weather Data (BMKG Integration)
 */
const SAFEROUTE_WEATHER_DATA = {
    city: "Semarang",
    province: "Jawa Tengah",
    condition: "Hujan Ringan",
    temp: 27,
    unit: "°C",
    humidity: 86,
    windSpeed: "14 km/jam",
    rainfallRate: "42 mm/jam (Tinggi)",
    radarStatus: "Awan Konvektif Terdeteksi di Wilayah Selatan & Pesisir",
    forecastHourly: [
        { time: "09:00", temp: 26, icon: "🌧️", condition: "Gerimis", rainProb: "40%" },
        { time: "11:00", temp: 27, icon: "🌧️", condition: "Hujan Sedang", rainProb: "65%" },
        { time: "13:00", temp: 28, icon: "⛈️", condition: "Hujan Lebat", rainProb: "85%" },
        { time: "15:00", temp: 27, icon: "⚡", condition: "Hujan Petir", rainProb: "90%" },
        { time: "17:00", temp: 26, icon: "🌧️", condition: "Hujan Ringan", rainProb: "60%" },
        { time: "19:00", temp: 25, icon: "☁️", condition: "Berawan Tebal", rainProb: "30%" },
        { time: "21:00", temp: 25, icon: "☁️", condition: "Berawan", rainProb: "20%" },
        { time: "23:00", temp: 24, icon: "🌙", condition: "Cerah Berawan", rainProb: "10%" }
    ]
};

if (typeof window !== "undefined") {
    window.SAFEROUTE_WEATHER_DATA = SAFEROUTE_WEATHER_DATA;
}
