"""
Tests unitaires du service de priorisation d'alarmes.

Vérifie :
- Le calcul du score pondéré (5 dimensions, échelle 0-100)
- L'ordre du plan d'action quotidien (rank)
- La gestion des cas limites (0 alarme, alarmes identiques)
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.services.prioritization import (
    AlarmPrioritizer,
    AlarmScoringInput,
    AlarmScore,
)


def _make_alarm(
    alarm_id: str,
    criticality: str = "3_medium",
    occurrences_last_30d: int = 2,
    is_active_now: bool = True,
    equipment_zone_is_occupied: bool = True,
    energy_impact_kwh_per_day: float | None = 10.0,
    age_hours: float = 2.0,
) -> AlarmScoringInput:
    """Helper : construit une alarme de test avec des défauts raisonnables."""
    return AlarmScoringInput(
        alarm_id=alarm_id,
        criticality=criticality,
        triggered_at=datetime.utcnow() - timedelta(hours=age_hours),
        occurrences_last_30d=occurrences_last_30d,
        is_active_now=is_active_now,
        equipment_zone_is_occupied=equipment_zone_is_occupied,
        energy_impact_kwh_per_day=energy_impact_kwh_per_day,
    )


class TestAlarmPrioritizer:
    def test_critical_alarm_scores_higher_than_info(self):
        """Une alarme critique doit avoir un score nettement supérieur à info."""
        prio = AlarmPrioritizer()
        critical = _make_alarm("CRIT", criticality="5_critical")
        info = _make_alarm("INFO", criticality="1_info")

        score_crit = prio.score(critical).score
        score_info = prio.score(info).score

        assert score_crit > score_info
        # Score sur 100, critique avec occupation + énergie doit dépasser 50
        assert score_crit > 50

    def test_energy_impact_increases_score(self):
        """À criticité égale, plus d'impact énergétique = score plus haut."""
        prio = AlarmPrioritizer()
        low_energy = _make_alarm("A", energy_impact_kwh_per_day=2.0)
        high_energy = _make_alarm("B", energy_impact_kwh_per_day=50.0)

        assert prio.score(high_energy).score > prio.score(low_energy).score

    def test_unoccupied_zone_lowers_score(self):
        """Une alarme dans une zone inoccupée pèse moins."""
        prio = AlarmPrioritizer()
        in_hours = _make_alarm("A", equipment_zone_is_occupied=True)
        off_hours = _make_alarm("B", equipment_zone_is_occupied=False)

        assert prio.score(in_hours).score > prio.score(off_hours).score

    def test_inactive_alarm_lowers_persistence(self):
        """Une alarme résolue (is_active_now=False) a une persistance pénalisée."""
        prio = AlarmPrioritizer()
        active = _make_alarm("A", is_active_now=True, age_hours=72)
        resolved = _make_alarm("B", is_active_now=False, age_hours=72)

        assert prio.score(active).score > prio.score(resolved).score

    def test_daily_action_plan_orders_by_score(self):
        """Le plan d'action quotidien doit ordonner les alarmes par score décroissant."""
        prio = AlarmPrioritizer()
        alarms = [
            _make_alarm("LOW", criticality="1_info", energy_impact_kwh_per_day=1.0),
            _make_alarm("HIGH", criticality="5_critical", energy_impact_kwh_per_day=40.0),
            _make_alarm("MED", criticality="3_medium", energy_impact_kwh_per_day=10.0),
        ]

        plan = prio.daily_action_plan(alarms, top_n=3)

        assert len(plan) == 3
        assert plan[0].alarm_id == "HIGH"
        assert plan[-1].alarm_id == "LOW"
        scores = [p.score for p in plan]
        assert scores == sorted(scores, reverse=True)
        # Rangs renseignés 1..N
        assert [p.rank for p in plan] == [1, 2, 3]

    def test_daily_action_plan_respects_top_n(self):
        """top_n limite bien le nombre de résultats."""
        prio = AlarmPrioritizer()
        alarms = [_make_alarm(f"A{i}") for i in range(10)]

        plan = prio.daily_action_plan(alarms, top_n=3)
        assert len(plan) == 3

    def test_empty_input_returns_empty_plan(self):
        """Pas d'alarme → plan vide, pas d'erreur."""
        prio = AlarmPrioritizer()
        plan = prio.daily_action_plan([], top_n=5)
        assert plan == []

    def test_score_is_bounded(self):
        """Score normalisé entre 0 et 100 quoi qu'il arrive."""
        prio = AlarmPrioritizer()
        extreme = _make_alarm(
            "EXTREME",
            criticality="5_critical",
            energy_impact_kwh_per_day=10000.0,    # valeur exagérée
            occurrences_last_30d=10000,
            age_hours=24 * 365,
        )
        result = prio.score(extreme)
        assert 0.0 <= result.score <= 100.0

    def test_score_breakdown_contains_all_dimensions(self):
        """Le breakdown expose les 5 sous-scores."""
        prio = AlarmPrioritizer()
        result = prio.score(_make_alarm("X"))
        assert set(result.breakdown.keys()) == {
            "criticality", "energy", "frequency", "persistence", "occupancy"
        }
        for v in result.breakdown.values():
            assert 0.0 <= v <= 1.0

    @pytest.mark.parametrize("criticality", [
        "1_info", "2_low", "3_medium", "4_high", "5_critical"
    ])
    def test_all_criticality_levels_produce_valid_score(self, criticality):
        prio = AlarmPrioritizer()
        result = prio.score(_make_alarm("X", criticality=criticality))
        assert 0.0 <= result.score <= 100.0

    def test_unknown_criticality_uses_default(self):
        """Une criticité inconnue utilise une valeur par défaut sans crash."""
        prio = AlarmPrioritizer()
        alarm = _make_alarm("X", criticality="zz_unknown")
        result = prio.score(alarm)
        assert isinstance(result, AlarmScore)
        assert 0.0 <= result.score <= 100.0
