from __future__ import annotations

from sqlalchemy import Column, Date, ForeignKey, Integer, String, Table
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


allocations_table = Table(
    "allocations",
    Base.metadata,
    Column("orderline_id", ForeignKey("order_lines.id"), primary_key=True),
    Column("batch_id", ForeignKey("batches.id"), primary_key=True),
)


class Batch(Base):
    __tablename__ = "batches"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    reference: Mapped[str] = mapped_column(String(255))
    sku: Mapped[str] = mapped_column(String(255))
    eta: Mapped[Date | None] = mapped_column(Date, nullable=True)
    purchased_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    allocations: Mapped[set[OrderLine]] = relationship(
        secondary=allocations_table, back_populates="batches"
    )


class OrderLine(Base):
    __tablename__ = "order_lines"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    orderid: Mapped[str] = mapped_column(String(255))
    sku: Mapped[str] = mapped_column(String(255))
    qty: Mapped[int] = mapped_column(Integer, nullable=False)

    batches: Mapped[list[Batch]] = relationship(
        secondary=allocations_table, back_populates="allocations"
    )
