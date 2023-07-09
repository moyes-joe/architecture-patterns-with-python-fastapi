import os


def get_postgres_uri():
    host = os.environ.get("DB_HOST", "localhost")
    port = 54321 if host == "localhost" else 5432
    password = os.environ.get("DB_PASSWORD", "abc123")
    user, db_name = "allocation", "allocation"
    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"


class Config:
    PROJECT_NAME: str = "Architecture Patterns with Python"
    API_V1_STR: str = "/api/v1"
    POSTGRES_URI: str = get_postgres_uri()


config = Config()
