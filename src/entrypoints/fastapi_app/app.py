from __future__ import annotations

from functools import cache

from fastapi import APIRouter, Depends, FastAPI, HTTPException

from src.config import config
from src.domain import events
from src.service_layer import handlers, messagebus, unit_of_work

from .deps import get_unit_of_work
from .schemas import BatchRef

app = FastAPI(
    title=config.PROJECT_NAME, openapi_url=f"{config.API_V1_STR}/openapi.json"
)

router = APIRouter()


@app.on_event("startup")
@cache  # run once per process
def startup_event() -> None:
    from src.adapters.orm import start_mappers

    start_mappers()


@router.post("/batches", status_code=201)
def add_batch_endpoint(
    batch_create: events.BatchCreated,
    unit_of_work: unit_of_work.UnitOfWork = Depends(get_unit_of_work),  # noqa: B008
) -> dict[str, str]:
    messagebus.handle(event=batch_create, uow=unit_of_work)
    return {"message": "OK"}


@router.post("/allocations", status_code=201)
def allocate_endpoint(
    allocation_required: events.AllocationRequired,
    unit_of_work: unit_of_work.UnitOfWork = Depends(get_unit_of_work),  # noqa: B008
) -> BatchRef:
    try:
        results = messagebus.handle(event=allocation_required, uow=unit_of_work)
        batchref = results.pop(0)
    except (handlers.InvalidSku, handlers.InvalidRef) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if batchref is None:
        raise HTTPException(status_code=400, detail="Out of stock")

    return BatchRef(batchref=batchref)


app.include_router(router, prefix=config.API_V1_STR)
