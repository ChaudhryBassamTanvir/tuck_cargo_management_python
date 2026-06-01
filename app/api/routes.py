from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.cargo import CargoCreate, CargoUpdate, CargoOut, TruckCreate, TruckOut
from app.services import cargo_service
from app.core.events import publish_event
from typing import List
import uuid

router = APIRouter()

@router.post("/trucks", response_model=TruckOut)
async def add_truck(data: TruckCreate, db: AsyncSession = Depends(get_db)):
    return await cargo_service.create_truck(db, data)

@router.get("/trucks", response_model=List[TruckOut])
async def get_trucks(db: AsyncSession = Depends(get_db)):
    return await cargo_service.list_trucks(db)

@router.post("/cargos", response_model=CargoOut)
async def add_cargo(data: CargoCreate, db: AsyncSession = Depends(get_db)):
    cargo = await cargo_service.create_cargo(db, data)
    await publish_event("cargo.created", {"id": str(cargo.id), "weight": cargo.weight_kg})
    return cargo

@router.get("/cargos", response_model=List[CargoOut])
async def get_cargos(db: AsyncSession = Depends(get_db)):
    return await cargo_service.list_cargos(db)

@router.patch("/cargos/{cargo_id}", response_model=CargoOut)
async def update_cargo(cargo_id: uuid.UUID, data: CargoUpdate, db: AsyncSession = Depends(get_db)):
    try:
        cargo = await cargo_service.update_cargo_status(db, cargo_id, data)
        await publish_event("cargo.updated", {"id": str(cargo_id), "status": str(data.status)})
        return cargo
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))