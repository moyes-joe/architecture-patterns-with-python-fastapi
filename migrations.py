from __future__ import annotations

import pathlib

from alembic import command
from alembic.config import Config
from src.config import config

BASE_PATH = pathlib.Path(__file__).parent.absolute()


def load_alembic_config(dsn: str) -> Config:
    alembic_cfg = Config(str(BASE_PATH / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(BASE_PATH / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", dsn)
    return alembic_cfg


def upgrade_migrations(dsn: str) -> None:
    alembic_cfg = load_alembic_config(dsn)
    command.upgrade(alembic_cfg, "head")


def downgrade_migrations(dsn: str) -> None:
    alembic_cfg = load_alembic_config(dsn)
    command.downgrade(alembic_cfg, "base")


if __name__ == "__main__":
    upgrade_migrations(config.POSTGRES_URI)
