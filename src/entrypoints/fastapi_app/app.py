from __future__ import annotations

from fastapi import APIRouter, Depends, FastAPI, HTTPException

from src.config import config
from src.domain import model
from src.service_layer import services, unit_of_work

from .deps import get_unit_of_work
from .schemas import BatchCreate, BatchRef, OrderLineCreate

app = FastAPI(
    title=config.PROJECT_NAME, openapi_url=f"{config.API_V1_STR}/openapi.json"
)

router = APIRouter()


@router.post("/batches", status_code=201)
def add_batch_endpoint(
    batch_create: BatchCreate,
    unit_of_work: unit_of_work.UnitOfWorkProtocol = Depends(  # noqa: B008
        get_unit_of_work
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
        get_unit_of_work
    ),
) -> BatchRef:
    try:
        batchref = services.allocate(
            orderid=order_line_create.orderid,
            sku=order_line_create.sku,
            qty=order_line_create.qty,
            uow=unit_of_work,
        )
    except (model.OutOfStock, services.InvalidSku) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return BatchRef(batchref=batchref)


app.include_router(router, prefix=config.API_V1_STR)
