from stremio_catalog_provider.config.app_config import AppConfig


def test_app_config_normalizes_base_url():
    # Test url without trailing slash
    config = AppConfig(base_url="https://example.com")
    assert config.base_url == "https://example.com/"

    # Test url with trailing slash
    config = AppConfig(base_url="https://example.com/")
    assert config.base_url == "https://example.com/"

    # Test empty url
    config = AppConfig(base_url=None)
    assert config.base_url is None
