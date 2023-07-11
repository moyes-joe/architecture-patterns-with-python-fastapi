from __future__ import annotations

from sqlalchemy import Column, Date, ForeignKey, Integer, String, Table, event
from sqlalchemy.orm import registry, relationship

from src.domain import model

mapper_registry = registry()


order_lines = Table(
    "order_lines",
    mapper_registry.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("sku", String(255)),
    Column("qty", Integer, nullable=False),
    Column("orderid", String(255)),
)

products = Table(
    "products",
    mapper_registry.metadata,
    Column("sku", String(255), primary_key=True),
    Column("version_number", Integer, nullable=False, server_default="0"),
)

batches = Table(
    "batches",
    mapper_registry.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("reference", String(255)),
    Column("sku", ForeignKey("products.sku")),
    Column("purchased_quantity", Integer, nullable=False),
    Column("eta", Date, nullable=True),
)

allocations = Table(
    "allocations",
    mapper_registry.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("orderline_id", ForeignKey("order_lines.id")),
    Column("batch_id", ForeignKey("batches.id")),
)


def start_mappers() -> None:
    order_lines_mapper = mapper_registry.map_imperatively(model.OrderLine, order_lines)

    batches_mapper = mapper_registry.map_imperatively(
        model.Batch,
        batches,
        properties={
            "allocations": relationship(
                order_lines_mapper, secondary=allocations, collection_class=set
            )
        },
    )

    mapper_registry.map_imperatively(
        model.Product,
        products,
        properties={
            "batches": relationship(batches_mapper),
        },
    )


@event.listens_for(model.Product, "load")
def receive_load(product, _):
    product.messages = []
