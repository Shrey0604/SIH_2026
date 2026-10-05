from app.config import Settings
from app.db import initialize_database


def main() -> None:
    settings = Settings.from_env()
    repository = initialize_database(settings)
    counts = repository.counts()
    print(
        "Seed ready: "
        f"{counts['wells']} wells, {counts['events']} events, "
        f"{counts['evidence']} evidence records"
    )


if __name__ == "__main__":
    main()
