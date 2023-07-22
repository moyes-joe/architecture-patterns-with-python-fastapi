from __future__ import annotations

import os


def _get_redis_host_and_port():
    host = os.environ.get("REDIS_HOST", "localhost")
    port = 63791 if host == "localhost" else 6379
    return dict(host=host, port=port)


class Config:
    PROJECT_NAME: str = "Architecture Patterns with Python"
    API_V1_STR: str = "/api/v1"
    POSTGRES_URI: str = "postgresql://user:password@db:5432/app_db"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    def get_redis_host_and_port(self) -> dict[str, str | int]:
        return _get_redis_host_and_port()


config = Config()
