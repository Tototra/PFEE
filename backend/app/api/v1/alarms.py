"""Endpoints API — Alarmes et plan d'action quotidien."""

from datetime import datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.prioritization import AlarmPrioritizer, AlarmScoringInput

router = APIRouter(prefix="/alarms")


class AlarmOut(BaseModel):
    alarm_id: str
    code: str
    label: str
    equipment_name: str
    criticality: str
    triggered_at: datetime
    is_active: bool


class PrioritizedAlarmOut(BaseModel):
    alarm_id: str
    rank: int
    score: float
    breakdown: dict[str, float]


@router.get("/active", response_model=list[AlarmOut])
async def list_active_alarms() -> list[AlarmOut]:
    """Liste les alarmes actuellement actives.

    TODO: requête DB + jointure avec AlarmDefinition pour le label enrichi.
    """
    return []


@router.get("/action-plan/daily", response_model=list[PrioritizedAlarmOut])
async def daily_action_plan(top_n: int = 10) -> list[PrioritizedAlarmOut]:
    """Plan d'action quotidien — top N alarmes priorisées.

    Sprint S18-S20 — T7.1.
    """
    # Placeholder : récupérer les alarmes actives en DB puis appliquer le prioritizer
    now = datetime.utcnow()
    sample_alarms = [
        AlarmScoringInput(
            alarm_id="ALM_001",
            criticality="4_high",
            triggered_at=now - timedelta(hours=3),
            occurrences_last_30d=2,
            is_active_now=True,
            equipment_zone_is_occupied=True,
            energy_impact_kwh_per_day=12.0,
        ),
        AlarmScoringInput(
            alarm_id="ALM_002",
            criticality="3_medium",
            triggered_at=now - timedelta(days=2),
            occurrences_last_30d=8,
            is_active_now=True,
            equipment_zone_is_occupied=True,
            energy_impact_kwh_per_day=20.0,
        ),
    ]
    prioritizer = AlarmPrioritizer()
    ranked = prioritizer.daily_action_plan(sample_alarms, top_n=top_n)
    return [
        PrioritizedAlarmOut(
            alarm_id=s.alarm_id,
            rank=s.rank,
            score=s.score,
            breakdown=s.breakdown,
        )
        for s in ranked
    ]
