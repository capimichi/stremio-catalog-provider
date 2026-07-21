import base64
import respx
import httpx
from stremio_catalog_provider.config.torrserver_config import TorrServerConfig
from stremio_catalog_provider.client.torrserver_client import TorrServerClient

@respx.mock
def test_add_torrent_success_without_auth() -> None:
    respx.post("http://local:8090/torrents").mock(
        return_value=httpx.Response(200, json={"hash": "abc123hash"})
    )

    client = TorrServerClient(TorrServerConfig("http://local:8090"))
    info_hash = client.add_torrent("magnet:?xt=urn:btih:...")
    assert info_hash == "abc123hash"

@respx.mock
def test_add_torrent_success_with_auth() -> None:
    def custom_response(request: httpx.Request) -> httpx.Response:
        auth_header = request.headers.get("Authorization")
        assert auth_header is not None
        assert auth_header.startswith("Basic ")
        encoded_creds = auth_header.split(" ")[1]
        decoded = base64.b64decode(encoded_creds).decode("utf-8")
        assert decoded == "user:pass"
        return httpx.Response(200, json={"hash": "auth123hash"})

    respx.post("http://local:8090/torrents").mock(side_effect=custom_response)

    client = TorrServerClient(TorrServerConfig("http://local:8090", "user", "pass"))
    info_hash = client.add_torrent("magnet:?xt=urn:btih:...")
    assert info_hash == "auth123hash"

@respx.mock
def test_get_torrent_files_success() -> None:
    respx.post("http://local:8090/torrents").mock(
        return_value=httpx.Response(200, json={"file_stats": [{"id": 1, "path": "movie.mp4"}]})
    )

    client = TorrServerClient(TorrServerConfig("http://local:8090"))
    files = client.get_torrent_files("hash123")
    assert len(files) == 1
    assert files[0]["path"] == "movie.mp4"

@respx.mock
def test_remove_torrent_success() -> None:
    route = respx.post("http://local:8090/torrents").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )

    client = TorrServerClient(TorrServerConfig("http://local:8090"))
    client.remove_torrent("hash123")
    assert route.called
