import time
from typing import Any
from injector import inject
from stremio_catalog_provider.command.abstract_command import AbstractCommand
from stremio_catalog_provider.service.torrent_process_service import TorrentProcessService

class WorkerCommand(AbstractCommand):
    """Click Command to start the background worker process."""

    command_name: str = "worker"

    @inject
    def __init__(self, process_service: TorrentProcessService) -> None:
        self.process_service = process_service

    def run(self, **kwargs: Any) -> None:
        """Starts the worker polling loop."""
        print("Avvio Background Worker in polling...")
        while True:
            processed = self.process_service.process_next_torrent()
            if not processed:
                time.sleep(5)
