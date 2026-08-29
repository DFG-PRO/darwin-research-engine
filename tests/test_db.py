from sqlalchemy.engine import make_url

from darwin.config import Settings
from darwin.db import Base, get_engine, get_session_factory


def test_database_url_uses_postgresql_driver() -> None:
    settings = Settings(_env_file=None)
    url = make_url(settings.database_url)

    assert url.drivername == "postgresql+psycopg"


def test_declarative_base_metadata_exists() -> None:
    assert Base.metadata is not None


def test_session_factory_can_be_created_without_connecting() -> None:
    settings = Settings(database_url="postgresql+psycopg://user:pass@localhost:5432/darwin")
    engine = get_engine(settings)
    session_factory = get_session_factory(settings)

    assert engine.url.drivername == "postgresql+psycopg"
    assert session_factory.kw["bind"].url.database == "darwin"
