from __future__ import annotations

from collections.abc import Callable, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import clear_mappers, sessionmaker

from src.adapters.orm import mapper_registry, start_mappers
from src.config import config
from src.entrypoints.fastapi_app.app import app
from src.entrypoints.fastapi_app.deps import get_engine


@pytest.fixture(scope="session", autouse=True)
def start_clear_mappers() -> Generator[None, None, None]:
    start_mappers()
    yield
    clear_mappers()


@pytest.fixture
def in_memory_db() -> Engine:
    engine = create_engine("sqlite:///:memory:")
    mapper_registry.metadata.create_all(engine)
    return engine


@pytest.fixture
def session_factory(in_memory_db) -> Generator[sessionmaker, None, None]:
    yield sessionmaker(bind=in_memory_db)


@pytest.fixture
def session(session_factory) -> Generator[sessionmaker, None, None]:
    return session_factory()


@pytest.fixture
def client(in_memory_engine: Engine) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_engine] = lambda: in_memory_engine

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def postgres_db() -> Generator[Engine, None, None]:
    engine = create_engine(config.POSTGRES_URI, isolation_level="REPEATABLE READ")
    mapper_registry.metadata.create_all(engine)
    yield engine


@pytest.fixture
def postgres_session_factory(
    postgres_db: Engine,
) -> Generator[sessionmaker, None, None]:
    yield sessionmaker(bind=postgres_db)


@pytest.fixture
def postgres_session(
    postgres_session_factory: Callable[[], sessionmaker]
) -> Generator[sessionmaker, None, None]:
    yield postgres_session_factory()


@pytest.fixture
def postgres_client(postgres_db: Engine) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_engine] = lambda: postgres_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
