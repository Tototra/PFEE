"""
Seed de données de démonstration pour Coach IA GTB.

Crée un site fictif (Bâtiment AER Le Kremlin-Bicêtre) avec :
- 2 équipements CVC (chaudière gaz + CTA)
- 8 points GTB représentatifs
- 4 définitions d'alarmes
- 3 cas de troubleshooting alimentant le RAG

Usage :
    python -m scripts.seed_demo_data
    # ou via Make
    make seed
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from sqlalchemy import select

from app.core.database import async_session_factory, engine, Base
from app.models.gtb import (
    AlarmCriticality,
    AlarmDefinition,
    Equipment,
    Point,
    PointType,
    Site,
    TroubleshootingCase,
)


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        result = await db.execute(select(Site).where(Site.code == "AER-KB"))
        if result.scalar_one_or_none():
            print("→ Site AER-KB déjà présent, seed ignoré.")
            return

        # ----- Site -----
        site = Site(
            code="AER-KB",
            name="Bâtiment AER Le Kremlin-Bicêtre",
            latitude=48.8099,
            longitude=2.3614,
        )
        db.add(site)
        await db.flush()

        # ----- Équipements -----
        chaudiere = Equipment(
            site_id=site.id,
            code="CHAUD-01",
            name="Chaudière gaz à condensation",
            equipment_type="boiler",
            zone="local_technique",
            metadata_json={"manufacturer": "Viessmann", "model": "Vitocrossal 300"},
        )
        cta = Equipment(
            site_id=site.id,
            code="CTA-RDC",
            name="CTA bureaux RDC",
            equipment_type="ahu",
            zone="rdc",
            metadata_json={"manufacturer": "Aldes", "model": "DFE+ 5000"},
        )
        db.add_all([chaudiere, cta])
        await db.flush()

        # ----- Points GTB -----
        points = [
            Point(
                site_id=site.id,
                equipment_id=chaudiere.id,
                external_id="AER-KB/CHAUD-01/T_DEP",
                name="Température départ chaudière",
                point_type=PointType.TEMPERATURE,
                unit="°C",
            ),
            Point(
                site_id=site.id,
                equipment_id=chaudiere.id,
                external_id="AER-KB/CHAUD-01/T_RET",
                name="Température retour chaudière",
                point_type=PointType.TEMPERATURE,
                unit="°C",
            ),
            Point(
                site_id=site.id,
                equipment_id=chaudiere.id,
                external_id="AER-KB/CHAUD-01/SP",
                name="Consigne chaudière",
                point_type=PointType.SETPOINT,
                unit="°C",
            ),
            Point(
                site_id=site.id,
                equipment_id=chaudiere.id,
                external_id="AER-KB/CHAUD-01/ETAT",
                name="État chaudière",
                point_type=PointType.STATE,
            ),
            Point(
                site_id=site.id,
                equipment_id=cta.id,
                external_id="AER-KB/CTA-RDC/T_SOUF",
                name="Température soufflage CTA",
                point_type=PointType.TEMPERATURE,
                unit="°C",
            ),
            Point(
                site_id=site.id,
                equipment_id=cta.id,
                external_id="AER-KB/CTA-RDC/T_REP",
                name="Température reprise CTA",
                point_type=PointType.TEMPERATURE,
                unit="°C",
            ),
            Point(
                site_id=site.id,
                equipment_id=cta.id,
                external_id="AER-KB/CTA-RDC/CO2",
                name="CO2 zone bureaux RDC",
                point_type=PointType.CO2,
                unit="ppm",
            ),
            Point(
                site_id=site.id,
                equipment_id=cta.id,
                external_id="AER-KB/CTA-RDC/ETAT",
                name="État CTA",
                point_type=PointType.STATE,
            ),
        ]
        db.add_all(points)

        # ----- Définitions d'alarmes -----
        alarms = [
            AlarmDefinition(
                code="A_DEFAUT_BRULEUR",
                label="Défaut brûleur",
                equipment_type="boiler",
                criticality=AlarmCriticality.HIGH.value,
                description="Le brûleur ne s'enclenche pas malgré la demande.",
                typical_causes=["encrassement électrode", "pression gaz insuffisante"],
                standard_actions=["vérifier électrode ionisation", "contrôler pression gaz"],
                trigger_conditions={"point": "ETAT_BRULEUR", "value": 0},
            ),
            AlarmDefinition(
                code="A_SURCHAUFFE",
                label="Surchauffe chaudière",
                equipment_type="boiler",
                criticality=AlarmCriticality.CRITICAL.value,
                description="Température départ > seuil de sécurité.",
                typical_causes=["défaut vanne", "pompe circulateur arrêtée"],
                standard_actions=["arrêt d'urgence chaudière", "vérifier circulateur"],
                trigger_conditions={"point": "T_DEP", "operator": ">", "threshold": 85},
            ),
            AlarmDefinition(
                code="A_FILTRE_ENCRASSE",
                label="Filtre CTA encrassé",
                equipment_type="ahu",
                criticality=AlarmCriticality.MEDIUM.value,
                description="Perte de charge filtre dépasse le seuil maintenance.",
                typical_causes=["filtre saturé", "humidité filtre"],
                standard_actions=["remplacer filtre G4/F7", "vérifier état caisson"],
                trigger_conditions={"point": "DP_FILTRE", "operator": ">", "threshold": 150},
            ),
            AlarmDefinition(
                code="A_CO2_ELEVE",
                label="CO2 zone occupée élevé",
                equipment_type="ahu",
                criticality=AlarmCriticality.MEDIUM.value,
                description="CO2 > 1000 ppm en heures d'occupation.",
                typical_causes=["débit insuffisant", "free-cooling désactivé"],
                standard_actions=["augmenter débit soufflage", "vérifier détecteur CO2"],
                trigger_conditions={"point": "CO2", "operator": ">", "threshold": 1000},
            ),
        ]
        db.add_all(alarms)

        # ----- Cas de troubleshooting (alimentent le RAG) -----
        cases = [
            TroubleshootingCase(
                title="Défaut brûleur récurrent sur chaudière gaz",
                symptom="Le brûleur se met en sécurité plusieurs fois par jour, "
                        "souvent en début de cycle, sans alarme de gaz.",
                context={"equipment_type": "boiler", "frequency": "multiple_daily"},
                diagnosis="Encrassement de l'électrode d'ionisation et défaut "
                          "d'allumage progressif.",
                corrective_action=(
                    "1) Vérifier électrode ionisation (nettoyage). "
                    "2) Contrôler pression gaz amont. "
                    "3) Vérifier programmateur d'allumage. "
                    "4) Si récurrent : remplacer électrode."
                ),
                resolution_duration_minutes=90,
                source="CR-AER-2025-042",
            ),
            TroubleshootingCase(
                title="CTA — Température soufflage instable",
                symptom="La température de soufflage oscille de ±3°C autour de "
                        "la consigne sans converger.",
                context={"equipment_type": "ahu", "symptom_type": "oscillation"},
                diagnosis="PID mal réglé (gain trop élevé) ou capteur soufflage "
                          "mal positionné dans la gaine.",
                corrective_action=(
                    "1) Vérifier position du capteur (au moins 5×D après batterie). "
                    "2) Réajuster PID : réduire Kp de 30%, augmenter Ti. "
                    "3) Vérifier vanne 3 voies (jeu mécanique)."
                ),
                resolution_duration_minutes=120,
                source="CR-AER-2025-051",
            ),
            TroubleshootingCase(
                title="Consommation gaz anormalement élevée en mi-saison",
                symptom="La consommation gaz en avril/octobre est 40% supérieure "
                        "à la prévision DJU.",
                context={"equipment_type": "boiler", "season": "mid_season"},
                diagnosis="Loi d'eau non adaptée — pente trop forte, la chaudière "
                          "produit à 70°C même quand 50°C suffirait.",
                corrective_action=(
                    "1) Tracer la courbe T_dep en fonction de T_ext. "
                    "2) Calculer pente théorique selon déperditions. "
                    "3) Ajuster pente loi d'eau dans la régulation. "
                    "4) Vérifier en parallèle l'absence de fuite réseau."
                ),
                resolution_duration_minutes=180,
                source="CR-AER-2025-063",
            ),
        ]
        db.add_all(cases)

        await db.commit()

        print(
            f"✓ Seed terminé : site {site.code}, {len(points)} points, "
            f"{len(alarms)} alarmes, {len(cases)} cas RAG."
        )
        print(f"  Date : {datetime.utcnow().isoformat()}")


if __name__ == "__main__":
    asyncio.run(seed())
