from typing import Optional
from sqlalchemy import Integer, String, BigInteger, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from stremio_catalog_provider.entity.base import BaseEntity

class FileMapping(BaseEntity):
    """SQLAlchemy model representing a mapping between a torrent file and a MediaItem/Episode."""

    __tablename__ = "file_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    torrent_hash: Mapped[str] = mapped_column(
        ForeignKey("torrents.info_hash", ondelete="CASCADE"), nullable=False
    )
    file_index: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    media_item_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("media_items.id", ondelete="SET NULL"), nullable=True
    )
    episode_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("episodes.id", ondelete="SET NULL"), nullable=True
    )
    manually_corrected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
