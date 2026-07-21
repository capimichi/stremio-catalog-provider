from typing import Optional
from sqlalchemy import String, Integer, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column
from stremio_catalog_provider.entity.base import BaseEntity

class MediaItem(BaseEntity):
    """SQLAlchemy model representing a Media Item (Movie or Series)."""

    __tablename__ = "media_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    imdb_id: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    tmdb_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    type: Mapped[str] = mapped_column(Enum("movie", "series", name="media_type"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    poster_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    background_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
