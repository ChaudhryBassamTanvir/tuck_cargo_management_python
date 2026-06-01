from sqlalchemy import Column, String, Float, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.session import Base

class StatusEnum(str, enum.Enum):
    pending   = "pending"
    in_transit = "in_transit"
    delivered = "delivered"
    failed    = "failed"

class Truck(Base):
    __tablename__ = "trucks"
    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plate        = Column(String(20), unique=True, nullable=False)
    driver_name  = Column(String(100))
    capacity_kg  = Column(Float)
    cargos       = relationship("Cargo", back_populates="truck")

class Cargo(Base):
    __tablename__ = "cargos"
    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description  = Column(Text)
    weight_kg    = Column(Float)
    status       = Column(Enum(StatusEnum), default=StatusEnum.pending)
    truck_id     = Column(UUID(as_uuid=True), ForeignKey("trucks.id"), nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    truck        = relationship("Truck", back_populates="cargos")

class CargoEvent(Base):
    __tablename__ = "cargo_events"
    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cargo_id     = Column(UUID(as_uuid=True), ForeignKey("cargos.id"))
    event_type   = Column(String(50))
    payload      = Column(Text)
    created_at   = Column(DateTime, default=datetime.utcnow)