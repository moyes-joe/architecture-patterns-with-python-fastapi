from __future__ import annotations

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from src.adapters import repository
from src.config import config
from src.domain import model
from src.entrypoints.fastapi_app.deps import get_repository, get_session
from src.service_layer import services

from .schemas import BatchCreate, BatchRef, OrderLineCreate

app = FastAPI(
    title=config.PROJECT_NAME, openapi_url=f"{config.API_V1_STR}/openapi.json"
)

router = APIRouter()


@router.post("/batches", status_code=201)
def add_batch_endpoint(
    batch_create: BatchCreate,
    repo: repository.AbstractRepository[model.Batch] = Depends(  # noqa: B008
        get_repository
    ),
    session: Session = Depends(get_session),  # noqa: B008
) -> dict[str, str]:
    services.add_batch(
        ref=batch_create.reference,
        sku=batch_create.sku,
        qty=batch_create.qty,
        eta=batch_create.eta_date(),
        repo=repo,
        session=session,
    )
    return {"message": "OK"}


@router.post("/allocations", status_code=201)
def allocate_endpoint(
    order_line_create: OrderLineCreate,
    repo: repository.AbstractRepository[model.Batch] = Depends(  # noqa: B008
        get_repository
    ),
    session: Session = Depends(get_session),  # noqa: B008
) -> BatchRef:
    try:
        batchref = services.allocate(
            orderid=order_line_create.orderid,
            sku=order_line_create.sku,
            qty=order_line_create.qty,
            repo=repo,
            session=session,
        )
    except (model.OutOfStock, services.InvalidSku) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return BatchRef(batchref=batchref)


app.include_router(router, prefix=config.API_V1_STR)
