"""Agent IA — Diagnostic d'alarme (V1).

Le cœur de la valeur du Coach IA. Prend une alarme en entrée et produit :
  - Un diagnostic structuré (causes probables triées par probabilité)
  - Des actions correctives recommandées
  - Des références aux sources (RAG transparency)
  - Un niveau de confiance

Architecture :
  alarme + contexte GTB (mesures 24h) + météo + RAG (notices, cas similaires)
  → prompt structuré → LLM Mistral → réponse parsée
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.agents.llm_provider import LLMMessage, LLMProvider, LLMRole
from app.core.logging import get_logger
from app.rag.pipeline import RagPipeline

logger = get_logger(__name__)


SYSTEM_PROMPT = """Tu es un expert en Chauffage-Ventilation-Climatisation (CVC) et en supervision GTB (Gestion Technique du Bâtiment).

Ton rôle : aider un technicien d'exploitation à diagnostiquer et résoudre une alarme GTB.

Règles strictes :
1. Réponds TOUJOURS en français professionnel et concis.
2. Structure ta réponse en 4 sections : DIAGNOSTIC, CAUSES PROBABLES (triées par probabilité), ACTIONS RECOMMANDÉES (étapes ordonnées), POINTS DE VIGILANCE.
3. Base-toi STRICTEMENT sur le contexte fourni (mesures GTB, météo, sources documentaires). Si une information manque, dis-le clairement.
4. NE recommande JAMAIS d'action automatique sur l'installation : tes suggestions sont des aides à la décision humaine.
5. Cite tes sources via [Source: nom_document] quand tu t'appuies sur le RAG.
6. Pour chaque action, indique : équipement concerné, niveau d'urgence (immédiat / sous 24h / sous 1 semaine), compétence requise.
7. Si la situation présente un risque sécurité (gaz, électrique, surchauffe), commence par un encadré ⚠️ ALERTE SÉCURITÉ.
"""


@dataclass
class AlarmContext:
    """Contexte injecté dans le prompt pour le diagnostic."""

    alarm_code: str
    alarm_label: str
    alarm_timestamp: datetime
    equipment_name: str
    equipment_type: str
    site_name: str
    # Mesures GTB des dernières 24h sur les points pertinents
    recent_measurements: list[dict[str, Any]]
    # Météo actuelle + tendance
    weather_current: dict[str, Any] | None
    # Alarmes connexes (même équipement, dernière semaine)
    related_alarms: list[dict[str, Any]]


@dataclass
class DiagnosticResult:
    """Sortie structurée d'un diagnostic."""

    summary: str
    raw_response: str
    sources: list[dict[str, Any]]
    confidence: float
    latency_ms: int
    model: str
    safety_alert: bool


class DiagnosticAgent:
    """Agent de diagnostic d'alarme (V1 — agent unique).

    En Phase 2 du projet, cet agent pourra être éclaté en multi-agents
    (router → diagnostic / énergie / dépannage).
    """

    def __init__(
        self,
        llm: LLMProvider | None = None,
        rag: RagPipeline | None = None,
    ) -> None:
        self.llm = llm or LLMProvider()
        self.rag = rag or RagPipeline()

    async def diagnose(self, context: AlarmContext) -> DiagnosticResult:
        """Produit un diagnostic complet pour une alarme."""
        logger.info(
            "agent.diagnose.start",
            alarm=context.alarm_code,
            equipment=context.equipment_name,
        )

        # 1. Recherche RAG : alarme + équipement (tolérant aux pannes)
        rag_results: list = []
        try:
            rag_query = f"{context.alarm_label} {context.equipment_type} diagnostic dépannage"
            rag_results = self.rag.search(rag_query, top_k=5)
        except Exception as e:  # noqa: BLE001
            logger.warning("agent.rag.unavailable", error=str(e))
        sources_block = self._format_rag_sources(rag_results)

        # 2. Construction du prompt avec contexte structuré
        context_block = self._format_context(context)

        user_prompt = f"""ALARME ACTIVE :
- Code : {context.alarm_code}
- Libellé : {context.alarm_label}
- Déclenchement : {context.alarm_timestamp.isoformat()}
- Équipement : {context.equipment_name} ({context.equipment_type})
- Site : {context.site_name}

CONTEXTE GTB (dernières 24h) :
{context_block}

SOURCES DOCUMENTAIRES PERTINENTES :
{sources_block}

Produis ton diagnostic en suivant le format demandé."""

        messages = [
            LLMMessage(LLMRole.SYSTEM, SYSTEM_PROMPT),
            LLMMessage(LLMRole.USER, user_prompt),
        ]

        response = await self.llm.complete(messages)

        safety_alert = "⚠️ ALERTE SÉCURITÉ" in response.content
        # Estimation simple de confiance basée sur la qualité du RAG
        confidence = self._estimate_confidence(rag_results, context)

        result = DiagnosticResult(
            summary=response.content[:300],
            raw_response=response.content,
            sources=[
                {"source": r.source, "score": r.score, "snippet": r.content[:200]}
                for r in rag_results
            ],
            confidence=confidence,
            latency_ms=response.latency_ms,
            model=response.model,
            safety_alert=safety_alert,
        )
        logger.info(
            "agent.diagnose.done",
            alarm=context.alarm_code,
            confidence=confidence,
            latency_ms=response.latency_ms,
            safety=safety_alert,
        )
        return result

    def _format_context(self, ctx: AlarmContext) -> str:
        lines = []
        if ctx.weather_current:
            w = ctx.weather_current
            lines.append(
                f"- Météo actuelle : {w.get('temperature_c', '?')}°C, "
                f"humidité {w.get('humidity_pct', '?')}%, "
                f"nébulosité {w.get('cloud_cover_pct', '?')}%"
            )
        if ctx.recent_measurements:
            lines.append("- Mesures GTB significatives (dernières 24h) :")
            for m in ctx.recent_measurements[:20]:  # cap pour limiter tokens
                lines.append(
                    f"    • {m.get('point_name')}: {m.get('value')} {m.get('unit', '')} "
                    f"@ {m.get('timestamp')}"
                )
        if ctx.related_alarms:
            lines.append("- Alarmes connexes (7 derniers jours) :")
            for a in ctx.related_alarms[:10]:
                lines.append(f"    • {a.get('code')} - {a.get('label')} @ {a.get('timestamp')}")
        return "\n".join(lines) if lines else "(Aucun contexte additionnel disponible)"

    def _format_rag_sources(self, results: list) -> str:
        if not results:
            return "(Aucune source documentaire trouvée — utilise tes connaissances générales en CVC, en le précisant.)"
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"[{i}] Source: {r.source} (score: {r.score:.2f})\n{r.content[:500]}...")
        return "\n\n".join(lines)

    def _estimate_confidence(self, rag_results: list, ctx: AlarmContext) -> float:
        """Heuristique simple de confiance.

        En V2 : utiliser un modèle calibré ou un LLM-as-a-judge.
        """
        score = 0.5
        if rag_results:
            top_score = rag_results[0].score
            score += min(0.3, top_score * 0.3)
        if ctx.recent_measurements:
            score += 0.1
        if ctx.weather_current:
            score += 0.05
        return round(min(1.0, score), 2)
