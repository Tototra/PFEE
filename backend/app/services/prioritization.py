"""Moteur de priorisation des alarmes (Sprint S18-S20).

Calcule un score de priorité pour chaque alarme active afin de générer
le "plan d'action quotidien" de l'exploitant.

Score = criticité × impact_énergétique × fréquence × persistance × occupation_zone

Toutes les dimensions sont normalisées sur [0, 1] et le résultat sur [0, 100].
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


CRITICALITY_WEIGHTS = {
    "1_info": 0.2,
    "2_low": 0.4,
    "3_medium": 0.6,
    "4_high": 0.8,
    "5_critical": 1.0,
}


@dataclass
class AlarmScoringInput:
    """Données nécessaires au scoring d'une alarme."""

    alarm_id: str
    criticality: str  # AlarmCriticality.value
    triggered_at: datetime
    occurrences_last_30d: int
    is_active_now: bool
    equipment_zone_is_occupied: bool
    energy_impact_kwh_per_day: float | None  # impact estimé si non résolu


@dataclass
class AlarmScore:
    alarm_id: str
    score: float  # [0, 100]
    breakdown: dict[str, float]
    rank: int = 0  # rempli après tri


class AlarmPrioritizer:
    """Calcule le score de priorité d'une alarme."""

    def __init__(
        self,
        weight_criticality: float = 0.35,
        weight_energy: float = 0.25,
        weight_frequency: float = 0.15,
        weight_persistence: float = 0.15,
        weight_occupancy: float = 0.10,
    ) -> None:
        total = (
            weight_criticality
            + weight_energy
            + weight_frequency
            + weight_persistence
            + weight_occupancy
        )
        # Normalisation pour s'assurer que la somme = 1
        self.w_crit = weight_criticality / total
        self.w_energy = weight_energy / total
        self.w_freq = weight_frequency / total
        self.w_pers = weight_persistence / total
        self.w_occ = weight_occupancy / total

    def score(self, alarm: AlarmScoringInput, now: datetime | None = None) -> AlarmScore:
        now = now or datetime.utcnow()

        # 1. Criticité
        crit = CRITICALITY_WEIGHTS.get(alarm.criticality, 0.5)

        # 2. Impact énergétique normalisé (impact > 50 kWh/j = 1.0)
        energy_raw = alarm.energy_impact_kwh_per_day or 0.0
        energy = min(1.0, energy_raw / 50.0)

        # 3. Fréquence (récurrence sur 30 derniers jours, plafonnée à 20 occurrences)
        freq = min(1.0, alarm.occurrences_last_30d / 20.0)

        # 4. Persistance (durée depuis déclenchement, plafonnée à 7 jours)
        age_hours = max(0, (now - alarm.triggered_at).total_seconds() / 3600)
        pers = min(1.0, age_hours / (24 * 7))
        if not alarm.is_active_now:
            pers *= 0.3  # une alarme résolue est moins prioritaire qu'une active

        # 5. Occupation de la zone
        occ = 1.0 if alarm.equipment_zone_is_occupied else 0.4

        total = (
            crit * self.w_crit
            + energy * self.w_energy
            + freq * self.w_freq
            + pers * self.w_pers
            + occ * self.w_occ
        ) * 100

        return AlarmScore(
            alarm_id=alarm.alarm_id,
            score=round(total, 1),
            breakdown={
                "criticality": round(crit, 2),
                "energy": round(energy, 2),
                "frequency": round(freq, 2),
                "persistence": round(pers, 2),
                "occupancy": round(occ, 2),
            },
        )

    def rank_alarms(self, alarms: list[AlarmScoringInput]) -> list[AlarmScore]:
        """Classe toutes les alarmes par score décroissant."""
        scores = [self.score(a) for a in alarms]
        scores.sort(key=lambda s: s.score, reverse=True)
        for i, s in enumerate(scores, 1):
            s.rank = i
        logger.info("prioritizer.ranked", count=len(scores), top_score=scores[0].score if scores else 0)
        return scores

    def daily_action_plan(
        self,
        alarms: list[AlarmScoringInput],
        top_n: int = 10,
    ) -> list[AlarmScore]:
        """Produit le plan d'action quotidien (top N alarmes)."""
        ranked = self.rank_alarms(alarms)
        return ranked[:top_n]
