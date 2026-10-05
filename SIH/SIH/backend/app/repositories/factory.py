from app.config import Settings
from app.repositories.base import Repository
from app.repositories.postgres import PostgresRepository
from app.repositories.sqlite import SQLiteRepository


def create_repository(settings: Settings) -> Repository:
    if settings.data_backend == "supabase":
        return PostgresRepository(settings.database_url)
    return SQLiteRepository(settings.database_url)
