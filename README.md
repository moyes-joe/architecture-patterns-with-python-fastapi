# architecture-patterns-with-python-fastapi

```sh
docker-compose up -d
# docker-compose exec web alembic init migrations
docker-compose exec web alembic revision --autogenerate -m "Initial migration"
docker-compose exec web alembic upgrade head
docker-compose exec db psql --username=user --dbname=app_db
docker-compose exec web pytest
```
