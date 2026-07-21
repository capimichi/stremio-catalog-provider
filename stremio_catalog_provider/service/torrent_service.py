import re
from typing import Optional
from injector import inject
from stremio_catalog_provider.entity.torrent import Torrent
from stremio_catalog_provider.repository.torrent_repository import TorrentRepository

class TorrentService:
    """Service for managing torrent business logic."""

    @inject
    def __init__(self, repo: TorrentRepository) -> None:
        self.repo = repo

    def add_torrent(self, magnet_url: str, media_id: Optional[int] = None) -> Torrent:
        """Parses the info_hash from a magnet link and adds it to the queue."""
        match = re.search(r"btih:([a-fA-F0-9]{40})", magnet_url, re.IGNORECASE)
        if not match:
            raise ValueError("Invalid magnet link: info_hash not found")
        info_hash = match.group(1).lower()

        torrent = self.repo.get_by_hash(info_hash)
        if not torrent:
            torrent = Torrent(
                info_hash=info_hash,
                magnet_url=magnet_url,
                status="QUEUED",
                predefined_media_item_id=media_id
            )
            self.repo.add(torrent)
        return torrent

    def retry_torrent(self, info_hash: str) -> None:
        """Resets a torrent status back to QUEUED to retry processing."""
        torrent = self.repo.get_by_hash(info_hash)
        if torrent:
            torrent.status = "QUEUED"
            torrent.error_message = None
            self.repo.get_session().commit()

    def delete_torrent(self, info_hash: str) -> None:
        """Deletes a torrent by its info_hash."""
        self.repo.delete(info_hash)
