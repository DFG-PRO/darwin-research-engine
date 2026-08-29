"""SQLAlchemy declarative base for Darwin database models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for future SQLAlchemy ORM models."""
