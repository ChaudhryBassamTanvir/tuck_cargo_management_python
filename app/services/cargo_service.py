from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.cargo import Cargo, Truck, CargoEvent, StatusEnum
from app.schemas.cargo import CargoCreate, CargoUpdate
from loguru import logger
import json

async def _get_or_404(session: AsyncSession, model, id):
    obj = await session.get(model, id)
    if not obj:
        raise ValueError(f"{model.__name__} {id} not found")
    return obj

async def _log_event(session: AsyncSession, cargo_id, event_type: str, payload: dict):
    event = CargoEvent(cargo_id=cargo_id, event_type=event_type, payload=json.dumps(payload))
    session.add(event)
    logger.info(f"[EVENT] {event_type} cargo={cargo_id}")

async def create_truck(session: AsyncSession, data):
    truck = Truck(**data.model_dump())
    session.add(truck)
    await session.flush()
    return truck

async def list_trucks(session: AsyncSession):
    result = await session.execute(select(Truck))
    return result.scalars().all()

async def create_cargo(session: AsyncSession, data: CargoCreate):
    cargo = Cargo(**data.model_dump())
    session.add(cargo)
    await session.flush()
    await _log_event(session, cargo.id, "cargo_created", {"weight": cargo.weight_kg})
    return cargo

async def list_cargos(session: AsyncSession):
    result = await session.execute(select(Cargo))
    return result.scalars().all()

async def update_cargo_status(session: AsyncSession, cargo_id, data: CargoUpdate):
    cargo = await _get_or_404(session, Cargo, cargo_id)
    if data.status:
        cargo.status = data.status
    if data.truck_id:
        cargo.truck_id = data.truck_id
    await session.flush()
    await _log_event(session, cargo.id, "status_updated", {"status": str(data.status)})
    return cargo