from pathlib import Path

from app.repositories.base import Repository


class SeedService:
    def __init__(self, repository: Repository, fixture_path: Path):
        self.repository = repository
        self.fixture_path = fixture_path

    def initialize(self) -> None:
        self.repository.initialize()
        self.repository.seed_from_file(self.fixture_path)

