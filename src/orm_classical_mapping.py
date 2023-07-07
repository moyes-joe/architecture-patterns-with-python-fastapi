from __future__ import annotations

from sqlalchemy import Column, Date, ForeignKey, Integer, String, Table
from sqlalchemy.orm import registry, relationship

from src import model

mapper_registry = registry()


allocations_table = Table(
    "allocations",
    mapper_registry.metadata,
    Column("orderline_id", ForeignKey("order_lines.id"), primary_key=True),
    Column("batch_id", ForeignKey("batches.id"), primary_key=True),
)

batch_table = Table(
    "batches",
    mapper_registry.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("reference", String(255)),
    Column("sku", String(255)),
    Column("eta", Date),
    Column("purchased_quantity", Integer, nullable=False),
)

order_line_table = Table(
    "order_lines",
    mapper_registry.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("orderid", String(255)),
    Column("sku", String(255)),
    Column("qty", Integer, nullable=False),
)

mapper_registry.map_imperatively(
    model.Batch,
    batch_table,
    properties={
        "allocations": relationship(
            secondary=allocations_table, back_populates="batches"
        )
    },
)

mapper_registry.map_imperatively(
    model.OrderLine,
    order_line_table,
    properties={
        "batches": relationship(
            secondary=allocations_table, back_populates="allocations"
        )
    },
)
