from __future__ import annotations

from functools import cache

from fastapi import APIRouter, Depends, FastAPI, HTTPException

from src.config import config
from src.service_layer import services, unit_of_work

from .deps import get_event_publishing_unit_of_work
from .schemas import BatchCreate, BatchRef, OrderLineCreate

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
    batch_create: BatchCreate,
    unit_of_work: unit_of_work.UnitOfWorkProtocol = Depends(  # noqa: B008
        get_event_publishing_unit_of_work
    ),
) -> dict[str, str]:
    services.add_batch(
        ref=batch_create.ref,
        sku=batch_create.sku,
        qty=batch_create.qty,
        eta=batch_create.eta_date(),
        uow=unit_of_work,
    )
    return {"message": "OK"}


@router.post("/allocations", status_code=201)
def allocate_endpoint(
    order_line_create: OrderLineCreate,
    unit_of_work: unit_of_work.UnitOfWorkProtocol = Depends(  # noqa: B008
        get_event_publishing_unit_of_work
    ),
) -> BatchRef:
    try:
        batchref = services.allocate(
            orderid=order_line_create.orderid,
            sku=order_line_create.sku,
            qty=order_line_create.qty,
            uow=unit_of_work,
        )
    except services.InvalidSku as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if batchref is None:
        raise HTTPException(status_code=400, detail="Out of stock")

    return BatchRef(batchref=batchref)


app.include_router(router, prefix=config.API_V1_STR)
