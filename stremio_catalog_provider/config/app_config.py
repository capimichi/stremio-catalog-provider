from typing import Optional

class AppConfig:
    """Configuration for general application parameters."""

    def __init__(self, base_url: Optional[str] = None) -> None:
        if base_url and not base_url.endswith("/"):
            base_url += "/"
        self.base_url = base_url
