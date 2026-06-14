"""Service météo — intégration Open-Meteo.

API gratuite, pas de quota bloquant, données réelles + prévisions.
Doc : https://open-meteo.com/en/docs

Usage:
    weather = await WeatherService().get_current(lat=48.85, lon=2.35)
    forecast = await WeatherService().get_forecast(lat=48.85, lon=2.35, hours=48)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class WeatherPoint:
    """Un point de mesure météo."""

    timestamp: datetime
    temperature_c: float
    humidity_pct: float | None
    wind_speed_kmh: float | None
    cloud_cover_pct: float | None
    precipitation_mm: float | None


class WeatherService:
    """Client Open-Meteo avec cache léger en mémoire.

    En prod, intégrer Redis pour le cache (TTL = settings.weather_cache_ttl_seconds).
    """

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or settings.openmeteo_base_url

    async def get_current(self, lat: float, lon: float) -> WeatherPoint:
        """Récupère les conditions météo actuelles."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.base_url}/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,cloud_cover,precipitation",
                    "timezone": "auto",
                },
            )
            response.raise_for_status()
            data = response.json()
        current = data.get("current", {})
        return WeatherPoint(
            timestamp=datetime.fromisoformat(current["time"]),
            temperature_c=current.get("temperature_2m"),
            humidity_pct=current.get("relative_humidity_2m"),
            wind_speed_kmh=current.get("wind_speed_10m"),
            cloud_cover_pct=current.get("cloud_cover"),
            precipitation_mm=current.get("precipitation"),
        )

    async def get_forecast(
        self, lat: float, lon: float, hours: int = 48
    ) -> list[WeatherPoint]:
        """Prévisions horaires sur N heures."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.base_url}/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,cloud_cover,precipitation",
                    "forecast_days": max(1, min(7, hours // 24 + 1)),
                    "timezone": "auto",
                },
            )
            response.raise_for_status()
            data = response.json()
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        n = min(len(times), hours)
        points = []
        for i in range(n):
            points.append(
                WeatherPoint(
                    timestamp=datetime.fromisoformat(times[i]),
                    temperature_c=hourly["temperature_2m"][i],
                    humidity_pct=hourly.get("relative_humidity_2m", [None] * n)[i],
                    wind_speed_kmh=hourly.get("wind_speed_10m", [None] * n)[i],
                    cloud_cover_pct=hourly.get("cloud_cover", [None] * n)[i],
                    precipitation_mm=hourly.get("precipitation", [None] * n)[i],
                )
            )
        logger.debug("weather.forecast", lat=lat, lon=lon, points=len(points))
        return points

    async def get_degree_days(
        self, lat: float, lon: float, base_temp_c: float = 18.0, days: int = 30
    ) -> float:
        """Calcule les Degrés Jours Unifiés (DJU) sur N jours passés.

        Utile pour le module énergie (T9.1) — normalisation conso vs météo.
        Formule simplifiée : sum(max(0, base - temp_moyenne_journaliere))
        """
        from datetime import timedelta

        end = datetime.utcnow().date()
        start = end - timedelta(days=days)
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                "https://archive-api.open-meteo.com/v1/archive",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                    "daily": "temperature_2m_mean",
                    "timezone": "auto",
                },
            )
            response.raise_for_status()
            daily = response.json().get("daily", {})
        temps = daily.get("temperature_2m_mean", []) or []
        dju = sum(max(0.0, base_temp_c - t) for t in temps if t is not None)
        return round(dju, 1)
