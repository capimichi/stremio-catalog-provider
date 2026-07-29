from typing import Optional, List


class AppConfig:
    """Configuration for general application parameters."""

    def __init__(
        self, base_url: Optional[str] = None, supported_languages: Optional[str] = None
    ) -> None:
        if base_url and not base_url.endswith("/"):
            base_url += "/"
        self.base_url = base_url
        self.supported_languages: List[str] = [
            lang.strip().lower()
            for lang in (supported_languages or "ita,eng").split(",")
            if lang.strip()
        ]
