from __future__ import annotations

from typing import Generator

import pytest
from sqlalchemy import Engine, StaticPool, create_engine
from sqlalchemy.orm import Session

from src.orm import mapper_registry


@pytest.fixture
def in_memory_db() -> Engine:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return engine


@pytest.fixture
def session(in_memory_db: Engine) -> Generator[Session, None, None]:
    mapper_registry.metadata.create_all(in_memory_db)
    with Session(in_memory_db) as session:
        yield session
    mapper_registry.metadata.drop_all(in_memory_db)
