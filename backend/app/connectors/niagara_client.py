"""Connecteur Niagara — Couche C1 (Acquisition).

Implémente la lecture des points temps réel, des historiques et des alarmes
via l'API Obix REST de Niagara (Tridium / Honeywell).

Doc Niagara nécessaire (à demander à AER) :
  - URL Obix : généralement `https://<station>/obix/`
  - Authentification : Basic Auth ou token
  - Endpoints standards :
      GET /obix/config/         → arborescence des points
      GET /obix/histories/      → historiques
      GET /obix/alarm/          → alarmes actives

Stratégie d'intégration documentée dans :
  docs/integration_niagara_benchmark.md
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class NiagaraPoint:
    """Représentation d'un point GTB lu depuis Niagara."""

    external_id: str
    name: str
    value: float | bool | str | None
    unit: str | None
    timestamp: datetime
    quality: str = "good"  # good, uncertain, bad


@dataclass
class NiagaraAlarm:
    """Représentation d'une alarme Niagara."""

    external_id: str
    source_point: str
    timestamp: datetime
    message: str
    priority: int  # 1-255 dans Niagara, à mapper vers AlarmCriticality
    is_acked: bool
    is_active: bool


class NiagaraClient:
    """Client async pour l'API Obix REST de Niagara.

    Usage:
        async with NiagaraClient() as client:
            points = await client.list_points()
            for point in points:
                value = await client.read_point(point.external_id)
    """

    def __init__(
        self,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        verify_ssl: bool | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = (base_url or settings.niagara_base_url).rstrip("/")
        self.username = username or settings.niagara_username
        self.password = password or settings.niagara_password
        self.verify_ssl = verify_ssl if verify_ssl is not None else settings.niagara_verify_ssl
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> NiagaraClient:
        auth = (self.username, self.password) if self.username else None
        self._client = httpx.AsyncClient(
            base_url=f"{self.base_url}/obix",
            auth=auth,
            timeout=self.timeout,
            verify=self.verify_ssl,
            headers={"Accept": "application/xml"},  # Obix renvoie du XML
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("NiagaraClient doit être utilisé comme context manager async")
        return self._client

    # ─── Découverte ───────────────────────────────────────────────────────────

    async def list_points(self, path: str = "/config/") -> list[dict[str, Any]]:
        """Liste les points GTB en parcourant l'arborescence Obix.

        Note : implémentation simplifiée. En production il faut parser
        récursivement le XML Obix (utiliser `lxml`) et filtrer par type
        (`<real/>`, `<bool/>`, `<enum/>`, etc.).
        """
        logger.info("niagara.list_points.start", path=path)
        response = await self.client.get(path)
        response.raise_for_status()
        # TODO: parser XML Obix → liste de points canoniques
        # Pour le POC, on retourne une structure brute
        return [{"raw_xml": response.text, "path": path}]

    # ─── Lecture temps réel ───────────────────────────────────────────────────

    async def read_point(self, external_id: str) -> NiagaraPoint:
        """Lit la valeur courante d'un point."""
        logger.debug("niagara.read_point", point=external_id)
        response = await self.client.get(external_id)
        response.raise_for_status()
        # TODO: parser XML Obix → NiagaraPoint
        # Placeholder structurel :
        return NiagaraPoint(
            external_id=external_id,
            name=external_id.split("/")[-1],
            value=None,
            unit=None,
            timestamp=datetime.utcnow(),
        )

    async def read_points_batch(self, external_ids: list[str]) -> list[NiagaraPoint]:
        """Lit en parallèle plusieurs points (utilise les requêtes batch Obix si dispo)."""
        import asyncio

        tasks = [self.read_point(pid) for pid in external_ids]
        return await asyncio.gather(*tasks)

    # ─── Historiques ──────────────────────────────────────────────────────────

    async def read_history(
        self,
        point_external_id: str,
        start: datetime,
        end: datetime | None = None,
        limit: int = 10000,
    ) -> list[NiagaraPoint]:
        """Lit l'historique d'un point sur une période.

        Endpoint typique : `/obix/histories/{station}/{point_path}/~historyQuery`
        """
        end = end or datetime.utcnow()
        logger.info(
            "niagara.read_history",
            point=point_external_id,
            start=start.isoformat(),
            end=end.isoformat(),
        )
        params = {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "limit": limit,
        }
        history_path = f"/histories/{point_external_id}/~historyQuery"
        response = await self.client.get(history_path, params=params)
        response.raise_for_status()
        # TODO: parser XML Obix history → list[NiagaraPoint]
        return []

    # ─── Alarmes ──────────────────────────────────────────────────────────────

    async def list_active_alarms(self) -> list[NiagaraAlarm]:
        """Liste les alarmes actuellement actives."""
        logger.debug("niagara.list_active_alarms")
        response = await self.client.get("/alarm/")
        response.raise_for_status()
        # TODO: parser XML Obix → list[NiagaraAlarm]
        return []

    async def list_alarms_history(
        self, start: datetime, end: datetime | None = None
    ) -> list[NiagaraAlarm]:
        """Historique des alarmes sur une période."""
        end = end or datetime.utcnow()
        # TODO: implémenter selon la convention exacte fournie par AER
        return []


# ─── Service de polling pour ingestion temps réel ─────────────────────────────


class NiagaraPoller:
    """Polleur périodique des données Niagara.

    À lancer en tâche de fond (FastAPI lifespan ou worker dédié).
    Fréquence configurable via settings.niagara_poll_interval_seconds.
    """

    def __init__(self, point_ids: list[str], interval_s: int | None = None) -> None:
        self.point_ids = point_ids
        self.interval_s = interval_s or settings.niagara_poll_interval_seconds
        self._stop = False

    async def run(self) -> None:
        """Boucle de polling. À arrêter via `stop()`."""
        import asyncio

        logger.info("niagara.poller.start", points=len(self.point_ids), interval=self.interval_s)
        while not self._stop:
            try:
                async with NiagaraClient() as client:
                    points = await client.read_points_batch(self.point_ids)
                    # TODO: persister les mesures via MeasurementService
                    logger.debug("niagara.poller.tick", count=len(points))
            except Exception as e:  # noqa: BLE001
                logger.error("niagara.poller.error", error=str(e))
            await asyncio.sleep(self.interval_s)

    def stop(self) -> None:
        self._stop = True
