"""Endpoints API — Sites GTB."""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.core.database import DbSession
from app.models.gtb import Site

router = APIRouter(prefix="/sites")


class SiteOut(BaseModel):
    id: UUID
    name: str
    code: str
    latitude: float | None
    longitude: float | None
    timezone: str
    supervision_vendor: str

    class Config:
        from_attributes = True


class SiteCreate(BaseModel):
    name: str
    code: str
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timezone: str = "Europe/Paris"
    supervision_vendor: str = "niagara"
    supervision_url: str | None = None


@router.get("", response_model=list[SiteOut])
async def list_sites(db: DbSession) -> list[Site]:
    """Liste tous les sites supervisés."""
    result = await db.execute(select(Site).order_by(Site.name))
    return list(result.scalars().all())


@router.get("/{site_id}", response_model=SiteOut)
async def get_site(site_id: UUID, db: DbSession) -> Site:
    site = await db.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Site introuvable")
    return site


@router.post("", response_model=SiteOut, status_code=201)
async def create_site(payload: SiteCreate, db: DbSession) -> Site:
    site = Site(**payload.model_dump())
    db.add(site)
    await db.commit()
    await db.refresh(site)
    return site
