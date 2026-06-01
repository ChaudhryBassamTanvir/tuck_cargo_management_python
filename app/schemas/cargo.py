from pydantic import BaseModel, UUID4
from typing import Optional
from datetime import datetime
from app.models.cargo import StatusEnum

class TruckCreate(BaseModel):
    plate: str
    driver_name: Optional[str] = None
    capacity_kg: Optional[float] = None

class TruckOut(TruckCreate):
    id: UUID4
    class Config:
        from_attributes = True

class CargoCreate(BaseModel):
    description: str
    weight_kg: float
    truck_id: Optional[UUID4] = None

class CargoUpdate(BaseModel):
    status: Optional[StatusEnum] = None
    truck_id: Optional[UUID4] = None

class CargoOut(CargoCreate):
    id: UUID4
    status: StatusEnum
    created_at: datetime
    class Config:
        from_attributes = True