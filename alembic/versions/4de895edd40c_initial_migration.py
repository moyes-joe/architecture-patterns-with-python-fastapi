"""Initial migration

Revision ID: 4de895edd40c
Revises:
Create Date: 2023-07-10 11:11:07.033711

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "4de895edd40c"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "order_lines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sku", sa.String(length=255), nullable=True),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("orderid", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "products",
        sa.Column("sku", sa.String(length=255), nullable=False),
        sa.Column("version_number", sa.Integer(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("sku"),
    )
    op.create_table(
        "batches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("reference", sa.String(length=255), nullable=True),
        sa.Column("sku", sa.String(length=255), nullable=True),
        sa.Column("purchased_quantity", sa.Integer(), nullable=False),
        sa.Column("eta", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(
            ["sku"],
            ["products.sku"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "allocations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("orderline_id", sa.Integer(), nullable=True),
        sa.Column("batch_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["batches.id"],
        ),
        sa.ForeignKeyConstraint(
            ["orderline_id"],
            ["order_lines.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("allocations")
    op.drop_table("batches")
    op.drop_table("products")
    op.drop_table("order_lines")
    # ### end Alembic commands ###