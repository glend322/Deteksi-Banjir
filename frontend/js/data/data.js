/**
 * SafeRoute - Master Data Aggregator
 * Menggabungkan semua modul data terpisah menjadi SAFEROUTE_DATA
 */

const SAFEROUTE_DATA = {
    get appInfo() { return window.SAFEROUTE_APP_DATA || {}; },
    get weather() { return window.SAFEROUTE_WEATHER_DATA || {}; },
    get riskSummary() { return (window.SAFEROUTE_FLOOD_DATA && window.SAFEROUTE_FLOOD_DATA.riskSummary) || {}; },
    get floodPoints() { return (window.SAFEROUTE_FLOOD_DATA && window.SAFEROUTE_FLOOD_DATA.floodPoints) || []; },
    get floodPolygons() { return (window.SAFEROUTE_FLOOD_DATA && window.SAFEROUTE_FLOOD_DATA.floodPolygons) || []; },
    get routes() { return window.SAFEROUTE_ROUTES_DATA || {}; },
    get emergencyContacts() { return window.SAFEROUTE_CONTACTS_DATA || []; },
    get waterSensors() { return window.SAFEROUTE_SENSORS_DATA || []; },
    get shelters() { return window.SAFEROUTE_SENSORS_DATA || []; },
    get evacuationPoints() { return window.SAFEROUTE_SHELTERS_DATA || []; },
    get alerts() { return window.SAFEROUTE_ALERTS_DATA || []; },
    get floodGuide() { return window.SAFEROUTE_GUIDES_DATA || {}; },
    get history() { return window.SAFEROUTE_HISTORY_DATA || {}; }
};

if (typeof window !== "undefined") {
    window.SAFEROUTE_DATA = SAFEROUTE_DATA;
}
