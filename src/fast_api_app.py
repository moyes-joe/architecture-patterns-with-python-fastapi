from __future__ import annotations

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src import model, repository, services
from src.config import config
from src.fastapi_deps import get_repository, get_session

app = FastAPI(
    title=config.PROJECT_NAME, openapi_url=f"{config.API_V1_STR}/openapi.json"
)

router = APIRouter()


class OrderLineCreate(BaseModel):
    orderid: str
    sku: str
    qty: int


class BatchRef(BaseModel):
    batchref: str


@router.post("/allocations", status_code=201)
def allocate_endpoint(
    order_line_create: OrderLineCreate,
    repo: repository.AbstractRepository[model.Batch] = Depends(get_repository),
    session: Session = Depends(get_session),
) -> BatchRef:
    line = model.OrderLine(**order_line_create.model_dump())

    try:
        batchref = services.allocate(line=line, repo=repo, session=session)
    except (model.OutOfStock, services.InvalidSku) as e:
        raise HTTPException(status_code=400, detail=str(e))

    return BatchRef(batchref=batchref)


app.include_router(router, prefix=config.API_V1_STR)
