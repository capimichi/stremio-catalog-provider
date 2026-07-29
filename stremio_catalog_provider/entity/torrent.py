from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from stremio_catalog_provider.entity.base import BaseEntity

if TYPE_CHECKING:
    from stremio_catalog_provider.entity.file_mapping import FileMapping


class Torrent(BaseEntity):
    """SQLAlchemy model representing a Torrent."""

    __tablename__ = "torrents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    info_hash: Mapped[str] = mapped_column(
        String(40), unique=True, index=True, nullable=False
    )
    magnet_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("QUEUED", "PROCESSING", "PROCESSED", "FAILED", name="torrent_status"),
        default="QUEUED",
        index=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    media_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("media_items.id"), nullable=True
    )
    resolution: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    codec: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    quality: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    audio: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    languages: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationship back-reference
    mappings: Mapped[List["FileMapping"]] = relationship(
        "FileMapping", back_populates="torrent", cascade="all, delete-orphan"
    )
