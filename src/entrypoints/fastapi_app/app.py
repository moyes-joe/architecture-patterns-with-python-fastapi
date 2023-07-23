from __future__ import annotations

from functools import cache

from fastapi import APIRouter, Depends, FastAPI, HTTPException

from src import views
from src.config import config
from src.domain import commands, events
from src.service_layer import handlers, messagebus, unit_of_work

from .deps import get_unit_of_work

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
    batch_create: commands.CreateBatch,
    unit_of_work: unit_of_work.UnitOfWork = Depends(get_unit_of_work),  # noqa: B008
) -> dict[str, str]:
    messagebus.handle(message=batch_create, uow=unit_of_work)
    return {"message": "OK"}


@router.post("/allocations", status_code=201)
def allocate_endpoint(
    allocation_required: commands.Allocate,
    unit_of_work: unit_of_work.UnitOfWork = Depends(get_unit_of_work),  # noqa: B008
) -> events.AllocatedBatchRef:
    try:
        results = messagebus.handle(message=allocation_required, uow=unit_of_work)
        allocated_batch_ref = results.pop(0)
    except (handlers.InvalidSku, handlers.InvalidRef) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if allocated_batch_ref is None:
        raise HTTPException(status_code=400, detail="Out of stock")

    return allocated_batch_ref


@router.get("/allocations/{orderid}", status_code=200)
def allocations_view_endpoint(
    orderid: str,
    unit_of_work: unit_of_work.UnitOfWork = Depends(get_unit_of_work),  # noqa: B008
) -> list[events.AllocationsViewed]:
    result = views.allocations(orderid, unit_of_work)
    if not result:
        raise HTTPException(status_code=404, detail="not found")
    return result


app.include_router(router, prefix=config.API_V1_STR)
