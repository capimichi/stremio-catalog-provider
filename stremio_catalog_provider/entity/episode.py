from typing import Optional
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from stremio_catalog_provider.entity.base import BaseEntity

class Episode(BaseEntity):
    """SQLAlchemy model representing a TV Series Episode."""

    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    media_item_id: Mapped[int] = mapped_column(ForeignKey("media_items.id", ondelete="CASCADE"), nullable=False)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    episode: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
