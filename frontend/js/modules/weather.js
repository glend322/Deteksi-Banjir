/**
 * SafeRoute - Weather Module
 */

class WeatherModule {
    constructor(app) {
        this.app = app;
    }

    init() {
        const topbarWeather = document.getElementById("weatherWidgetBtn");
        if (topbarWeather) {
            topbarWeather.addEventListener("click", () => {
                this.app.openModal("modalWeather");
            });
        }
    }
}

if (typeof window !== "undefined") {
    window.WeatherModule = WeatherModule;
}
