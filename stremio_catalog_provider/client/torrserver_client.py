from typing import Any, Optional
import httpx
from injector import inject
from stremio_catalog_provider.config.torrserver_config import TorrServerConfig

class TorrServerClient:
    """HTTP Client for communicating with TorrServer."""

    @inject
    def __init__(self, config: TorrServerConfig) -> None:
        self.config = config
        self.auth: Optional[tuple[str, str]] = None
        if self.config.username and self.config.password:
            self.auth = (self.config.username, self.config.password)

    def add_torrent(self, magnet_url: str) -> str:
        """Adds a torrent to TorrServer and returns its info_hash."""
        endpoint = f"{self.config.base_url}/torrents"
        payload = {"action": "add", "link": magnet_url, "save_to_db": True}
        response = httpx.post(endpoint, json=payload, auth=self.auth, timeout=30.0)
        response.raise_for_status()
        info_hash = response.json().get("hash")
        if not isinstance(info_hash, str):
            raise ValueError("TorrServer did not return a valid hash string")
        return info_hash

    def get_torrent_files(self, info_hash: str) -> list[dict[str, Any]]:
        """Retrieves file statistics and details for a specific torrent from TorrServer."""
        endpoint = f"{self.config.base_url}/torrents"
        payload = {"action": "get", "hash": info_hash}
        response = httpx.post(endpoint, json=payload, auth=self.auth, timeout=30.0)
        response.raise_for_status()
        file_stats = response.json().get("file_stats", [])
        if isinstance(file_stats, list):
            return file_stats
        return []

    def remove_torrent(self, info_hash: str) -> None:
        """Removes/drops a torrent from TorrServer."""
        endpoint = f"{self.config.base_url}/torrents"
        payload = {"action": "drop", "hash": info_hash}
        response = httpx.post(endpoint, json=payload, auth=self.auth, timeout=30.0)
        response.raise_for_status()
