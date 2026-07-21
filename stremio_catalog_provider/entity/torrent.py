from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from stremio_catalog_provider.entity.base import BaseEntity

class Torrent(BaseEntity):
    """SQLAlchemy model representing a Torrent."""

    __tablename__ = "torrents"

    info_hash: Mapped[str] = mapped_column(String(40), primary_key=True)
    magnet_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("QUEUED", "PROCESSING", "PROCESSED", "FAILED", name="torrent_status"),
        default="QUEUED"
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    predefined_media_item_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("media_items.id"), nullable=True
    )
