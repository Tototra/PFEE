"""Endpoints API — Module énergie (Sprint S25-S27)."""

from datetime import datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.services.weather_service import WeatherService

router = APIRouter(prefix="/energy")


class EnergyAnalysisOut(BaseModel):
    period_start: datetime
    period_end: datetime
    total_kwh: float
    baseline_kwh: float
    deviation_pct: float
    degree_days: float
    drift_detected: bool


class OptimizationScenarioOut(BaseModel):
    id: str
    title: str
    description: str
    estimated_savings_kwh_year: float
    estimated_savings_eur_year: float
    confidence: float
    requires_human_validation: bool = True


@router.get("/analysis", response_model=EnergyAnalysisOut)
async def energy_analysis(days: int = 30) -> EnergyAnalysisOut:
    """Analyse consommation vs baseline météo-corrigée.

    TODO: récupérer index énergie réels en DB et calculer la baseline DJU.
    """
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    weather = WeatherService()
    dju = await weather.get_degree_days(
        lat=settings.default_site_lat,
        lon=settings.default_site_lon,
        days=days,
    )
    # Placeholder — calculs réels à brancher sur la DB
    return EnergyAnalysisOut(
        period_start=start,
        period_end=end,
        total_kwh=0.0,
        baseline_kwh=0.0,
        deviation_pct=0.0,
        degree_days=dju,
        drift_detected=False,
    )


@router.get("/optimizations", response_model=list[OptimizationScenarioOut])
async def list_optimizations() -> list[OptimizationScenarioOut]:
    """Scénarios d'optimisation énergétique suggérés.

    Garde-fou : validation humaine obligatoire avant action terrain.
    """
    return []
