class TorrServerConfig:
    """Configuration class for TorrServer client."""

    def __init__(self, base_url: str, username: str | None = None, password: str | None = None):
        self.base_url = base_url
        self.username = username
        self.password = password
