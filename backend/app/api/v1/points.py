"""Endpoints API — Points GTB et mesures."""

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.core.database import DbSession
from app.models.gtb import Point

router = APIRouter(prefix="/points")


class PointOut(BaseModel):
    id: UUID
    site_id: UUID
    equipment_id: UUID | None
    external_id: str
    name: str
    point_type: str
    unit: str | None
    is_active: bool

    class Config:
        from_attributes = True


class MeasurementOut(BaseModel):
    timestamp: datetime
    value: float
    quality: str = "good"


@router.get("", response_model=list[PointOut])
async def list_points(
    db: DbSession,
    site_id: UUID | None = None,
    point_type: str | None = None,
) -> list[Point]:
    """Liste les points GTB, filtrables par site et type."""
    query = select(Point)
    if site_id:
        query = query.where(Point.site_id == site_id)
    if point_type:
        query = query.where(Point.point_type == point_type)
    result = await db.execute(query.order_by(Point.name))
    return list(result.scalars().all())


@router.get("/{point_id}", response_model=PointOut)
async def get_point(point_id: UUID, db: DbSession) -> Point:
    point = await db.get(Point, point_id)
    if point is None:
        raise HTTPException(status_code=404, detail="Point introuvable")
    return point


@router.get("/{point_id}/measurements", response_model=list[MeasurementOut])
async def get_measurements(
    point_id: UUID,
    db: DbSession,
    hours: int = Query(default=24, ge=1, le=24 * 30),
) -> list[MeasurementOut]:
    """Récupère les mesures d'un point sur N heures (max 30j).

    TODO: requête sur la hypertable TimescaleDB `measurements`.
    Placeholder retournant une liste vide en attendant l'implémentation.
    """
    point = await db.get(Point, point_id)
    if point is None:
        raise HTTPException(status_code=404, detail="Point introuvable")
    # _ = datetime.utcnow() - timedelta(hours=hours)  # since
    return []
