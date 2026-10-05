from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url

from app.repositories.sqlalchemy_repository import SqlAlchemyRepository


class SQLiteRepository(SqlAlchemyRepository):
    def __init__(self, database_url: str):
        database_path = make_url(database_url).database
        if database_path and database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        super().__init__(database_url, connect_args={"check_same_thread": False})

    def initialize(self) -> None:
        super().initialize()
        columns = {column["name"] for column in inspect(self.engine).get_columns("wells")}
        if "well_scope" not in columns:
            with self.engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE wells ADD COLUMN well_scope VARCHAR(32) "
                        "NOT NULL DEFAULT 'LOCAL_OFFSET'"
                    )
                )
