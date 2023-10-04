from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Response

from src import bootstrap, views
from src.config import config
from src.domain import commands, events
from src.service_layer import handlers

if TYPE_CHECKING:
    from src.service_layer import messagebus

app = FastAPI(
    title=config.PROJECT_NAME, openapi_url=f"{config.API_V1_STR}/openapi.json"
)

router = APIRouter()


def fast_api_bootstrap() -> messagebus.MessageBus:
    return bootstrap.bootstrap()


@router.post("/batches", status_code=201)
def add_batch_endpoint(
    batch_create: commands.CreateBatch,
    bus: messagebus.MessageBus = Depends(fast_api_bootstrap),  # noqa: B008
) -> dict[str, str]:
    bus.handle(batch_create)
    return {"message": "OK"}


@router.post("/allocations", status_code=202)
def allocate_endpoint(
    allocate: commands.Allocate,
    bus: messagebus.MessageBus = Depends(fast_api_bootstrap),  # noqa: B008
) -> Response:
    try:
        bus.handle(allocate)  # type: ignore
    except (handlers.InvalidSku, handlers.InvalidRef) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return Response(status_code=202)


@router.get("/allocations/{orderid}", status_code=200)
def allocations_view_endpoint(
    orderid: str,
    bus: messagebus.MessageBus = Depends(fast_api_bootstrap),  # noqa: B008
) -> list[events.AllocationsViewed]:
    result = views.allocations(orderid, bus.uow)
    if not result:
        raise HTTPException(status_code=404, detail="not found")
    return result


app.include_router(router, prefix=config.API_V1_STR)
