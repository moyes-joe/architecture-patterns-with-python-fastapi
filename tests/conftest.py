from __future__ import annotations

from collections.abc import Callable, Generator

import psycopg2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, StaticPool, create_engine
from sqlalchemy.orm import Session

from migrations import downgrade_migrations, upgrade_migrations
from src.adapters.orm import mapper_registry
from src.config import config
from src.entrypoints.fastapi_app.app import app
from src.entrypoints.fastapi_app.deps import get_engine


@pytest.fixture
def in_memory_engine() -> Generator[Engine, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        # echo=True,
    )
    mapper_registry.metadata.create_all(engine)
    yield engine
    mapper_registry.metadata.drop_all(engine)


@pytest.fixture
def session(in_memory_engine: Engine) -> Generator[Session, None, None]:
    with Session(in_memory_engine) as session:
        yield session


@pytest.fixture
def session_factory(
    in_memory_engine: Engine,
) -> Generator[Callable[[], Session], None, None]:
    def _session_factory() -> Session:
        return Session(in_memory_engine)

    yield _session_factory


@pytest.fixture
def client(in_memory_engine: Engine) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_engine] = lambda: in_memory_engine

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# FIXME: Not used
@pytest.fixture(scope="session")
def postgres_database() -> None:
    dsn_parts = config.POSTGRES_URI.split("/")
    database_name = dsn_parts[-1]
    dsn = "/".join(dsn_parts[:-1] + ["postgres"])
    con = psycopg2.connect(dsn)
    con.autocommit = True
    cur = con.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS {database_name};")
    cur.execute(f"CREATE DATABASE {database_name};")


# FIXME: Not used
@pytest.fixture
@pytest.mark.usefixtures("postgres_database")
def postgres_session() -> Generator[Session, None, None]:
    dsn = config.POSTGRES_URI
    engine = create_engine(dsn, echo=False)
    session = Session(engine)
    upgrade_migrations(dsn)
    yield session
    session.close()
    downgrade_migrations(dsn)
    engine.dispose()
