from app.repositories.sqlalchemy_repository import SqlAlchemyRepository


class PostgresRepository(SqlAlchemyRepository):
    """Supabase/PostgreSQL implementation of the shared persistence boundary."""

