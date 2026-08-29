from pathlib import Path


def pytest_sessionstart() -> None:
    for path in Path("alembic/versions").glob("._*.py"):
        path.unlink(missing_ok=True)
