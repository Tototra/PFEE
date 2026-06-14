"""Moteur de règles métier CVC (Sprint S18-S20 — T7.2).

Règles encodées en YAML, lisibles et validables par les techniciens AER.

Exemples de règles :
  - Dérive consigne chaud/froid > 2°C pendant > 1h → alerte
  - Équipement actif hors plage horaire d'occupation → alerte
  - ΔT entrée/sortie échangeur < 2K sur 4h → suspicion d'encrassement
  - Index énergie progressant > 15% vs N-1 sur 7j → dérive consommation

Format YAML d'une règle :

  - id: deriv_setpoint_heating
    label: "Dérive consigne chauffage"
    description: "Écart température / consigne > 2°C pendant > 1h"
    when:
      equipment_type: boiler
      condition: |
        abs(measurement('zone_temp') - measurement('zone_setpoint')) > 2
      duration_minutes: 60
    then:
      severity: medium
      action: "Vérifier vanne 3 voies et sonde ambiance"
      energy_impact_kwh_per_day: 8
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import yaml

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Rule:
    """Une règle métier CVC."""

    id: str
    label: str
    description: str
    when: dict[str, Any]  # conditions (equipment_type, condition, duration_minutes)
    then: dict[str, Any]  # action (severity, action, energy_impact)


@dataclass
class RuleEvaluation:
    """Résultat d'évaluation d'une règle."""

    rule_id: str
    triggered: bool
    context: dict[str, Any]
    suggested_action: str | None = None
    severity: str | None = None
    energy_impact_kwh_per_day: float | None = None


class RulesEngine:
    """Moteur d'évaluation des règles métier CVC.

    Sécurité : l'évaluation des expressions `condition` se fait dans un
    contexte restreint (pas de `__builtins__`, pas d'`import`), avec
    uniquement des fonctions whitelisted (`measurement`, `abs`, `min`, `max`).
    """

    def __init__(self) -> None:
        self.rules: list[Rule] = []

    def load_from_yaml(self, path: str | Path) -> int:
        """Charge les règles depuis un fichier YAML."""
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or []
        self.rules = [Rule(**r) for r in data]
        logger.info("rules.loaded", count=len(self.rules), file=str(path))
        return len(self.rules)

    def evaluate_all(
        self,
        equipment_type: str,
        measurements_provider: Callable[[str], float | None],
        context: dict[str, Any] | None = None,
    ) -> list[RuleEvaluation]:
        """Évalue toutes les règles applicables à un équipement.

        Args:
            equipment_type: type d'équipement (boiler, ahu, pump, ...)
            measurements_provider: fonction `(point_name) -> valeur` qui résout
                les mesures actuelles dans le contexte.
            context: contexte additionnel (heure, occupation, etc.)
        """
        results: list[RuleEvaluation] = []
        for rule in self.rules:
            if rule.when.get("equipment_type") != equipment_type:
                continue
            triggered = self._evaluate_condition(
                rule.when.get("condition", ""), measurements_provider, context or {}
            )
            results.append(
                RuleEvaluation(
                    rule_id=rule.id,
                    triggered=triggered,
                    context=context or {},
                    suggested_action=rule.then.get("action") if triggered else None,
                    severity=rule.then.get("severity") if triggered else None,
                    energy_impact_kwh_per_day=rule.then.get("energy_impact_kwh_per_day")
                    if triggered
                    else None,
                )
            )
        return results

    def _evaluate_condition(
        self,
        expression: str,
        measurements_provider: Callable[[str], float | None],
        context: dict[str, Any],
    ) -> bool:
        """Évalue une condition Python dans un sandbox restreint.

        ⚠️ Sécurité : ne JAMAIS étendre `safe_builtins` sans audit.
        """
        if not expression:
            return False

        safe_builtins = {
            "abs": abs,
            "min": min,
            "max": max,
            "round": round,
            "len": len,
        }
        local_ns: dict[str, Any] = {
            "measurement": measurements_provider,
            **context,
        }
        global_ns = {"__builtins__": safe_builtins}

        try:
            result = eval(expression, global_ns, local_ns)  # noqa: S307
            return bool(result)
        except Exception as e:  # noqa: BLE001
            logger.warning("rules.eval.failed", expression=expression, error=str(e))
            return False
