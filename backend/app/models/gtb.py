"""Modèles SQLAlchemy — schéma canonique GTB.

Indépendant du fournisseur de supervision (Niagara, Schneider, Siemens, Distech).
Les tables `measurements` et `alarm_events` sont des hypertables TimescaleDB
(créées par la migration SQL — pas via SQLAlchemy).
"""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PointType(str, Enum):
    """Type d'un point GTB."""

    TEMPERATURE = "temperature"
    SETPOINT = "setpoint"
    HUMIDITY = "humidity"
    PRESSURE = "pressure"
    FLOW = "flow"
    STATE = "state"  # TOR
    ENERGY_INDEX = "energy_index"  # kWh
    POWER = "power"  # kW
    CO2 = "co2"
    OTHER = "other"


class AlarmCriticality(str, Enum):
    """Criticité des alarmes (1 = info, 5 = critique sécurité)."""

    INFO = "1_info"
    LOW = "2_low"
    MEDIUM = "3_medium"
    HIGH = "4_high"
    CRITICAL = "5_critical"


class Site(Base):
    """Un bâtiment ou site supervisé."""

    __tablename__ = "sites"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Paris")
    supervision_vendor: Mapped[str] = mapped_column(String(50), default="niagara")
    supervision_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    equipments: Mapped[list["Equipment"]] = relationship(back_populates="site")
    points: Mapped[list["Point"]] = relationship(back_populates="site")


class Equipment(Base):
    """Un équipement CVC (chaudière, CTA, PAC, vanne, etc.)."""

    __tablename__ = "equipments"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    site_id: Mapped[UUID] = mapped_column(ForeignKey("sites.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    equipment_type: Mapped[str] = mapped_column(String(50))  # boiler, ahu, pump, valve, ...
    zone: Mapped[str | None] = mapped_column(String(100))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    site: Mapped[Site] = relationship(back_populates="equipments")
    points: Mapped[list["Point"]] = relationship(back_populates="equipment")

    __table_args__ = (Index("ix_equipment_site_code", "site_id", "code", unique=True),)


class Point(Base):
    """Un point GTB (capteur, consigne, état, index)."""

    __tablename__ = "points"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    site_id: Mapped[UUID] = mapped_column(ForeignKey("sites.id"), nullable=False)
    equipment_id: Mapped[UUID | None] = mapped_column(ForeignKey("equipments.id"))
    external_id: Mapped[str] = mapped_column(String(500), nullable=False)  # ID Niagara
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    point_type: Mapped[str] = mapped_column(String(50))
    unit: Mapped[str | None] = mapped_column(String(20))  # °C, kWh, Pa, ...
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sampling_interval_s: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    site: Mapped[Site] = relationship(back_populates="points")
    equipment: Mapped[Equipment | None] = relationship(back_populates="points")

    __table_args__ = (Index("ix_point_site_external", "site_id", "external_id", unique=True),)


class AlarmDefinition(Base):
    """Référentiel d'alarmes enrichies (Phase 1 — T3.1)."""

    __tablename__ = "alarm_definitions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(300), nullable=False)
    equipment_type: Mapped[str] = mapped_column(String(50))
    criticality: Mapped[str] = mapped_column(String(20), default=AlarmCriticality.MEDIUM.value)
    description: Mapped[str | None] = mapped_column(Text)
    typical_causes: Mapped[list] = mapped_column(JSON, default=list)
    standard_actions: Mapped[list] = mapped_column(JSON, default=list)
    trigger_conditions: Mapped[dict] = mapped_column(JSON, default=dict)


class TroubleshootingCase(Base):
    """Cas de dépannage structurés pour alimenter le RAG (T3.2)."""

    __tablename__ = "troubleshooting_cases"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    symptom: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    diagnosis: Mapped[str] = mapped_column(Text, nullable=False)
    corrective_action: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str | None] = mapped_column(String(200))  # référence compte rendu
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class User(Base):
    """Utilisateur applicatif (technicien, exploitant, responsable énergie)."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="technician")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
