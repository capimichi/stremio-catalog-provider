class WebUiConfig:
    """Configuration class for the Web UI admin panel (Basic Auth)."""

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
