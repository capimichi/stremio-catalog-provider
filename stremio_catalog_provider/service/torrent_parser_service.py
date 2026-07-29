from typing import Any, Optional
import PTN
from injector import inject
from stremio_catalog_provider.config.app_config import AppConfig


class TorrentParserService:
    """Service to parse media filenames using PTN (Python Torrent Name parser)."""

    @inject
    def __init__(self, app_config: Optional[AppConfig] = None) -> None:
        self.app_config = app_config or AppConfig()

    LANGUAGE_KEYWORDS = {
        "ita": ["ita", "italian", "italiano"],
        "eng": ["eng", "english", "inglese"],
        "deu": ["deu", "german", "deutsch"],
        "fra": ["fra", "french", "francais"],
        "spa": ["spa", "spanish", "espanol"],
    }

    def parse_filename(self, filename: str) -> dict[str, Any]:
        """Parses a filename to extract title, season, episode, year, and metadata."""
        parsed = PTN.parse(filename)
        title = parsed.get("title")
        # Ensure we return a string for title
        if not isinstance(title, str) or not title:
            title = filename

        # PTN returns list of episodes/seasons sometimes if there's multiple, let's normalize to first item if it is a list
        season: Optional[int] = None
        season_val = parsed.get("season")
        if isinstance(season_val, list) and len(season_val) > 0:
            season = int(season_val[0])
        elif isinstance(season_val, int):
            season = season_val

        episode: Optional[int] = None
        episode_val = parsed.get("episode")
        if isinstance(episode_val, list) and len(episode_val) > 0:
            episode = int(episode_val[0])
        elif isinstance(episode_val, int):
            episode = episode_val

        year: Optional[int] = None
        year_val = parsed.get("year")
        if isinstance(year_val, int):
            year = year_val

        # Extract technical metadata
        resolution = parsed.get("resolution")
        if isinstance(resolution, list) and len(resolution) > 0:
            resolution = str(resolution[0])
        elif resolution:
            resolution = str(resolution)

        codec = parsed.get("codec")
        if isinstance(codec, list) and len(codec) > 0:
            codec = str(codec[0])
        elif codec:
            codec = str(codec)

        quality = parsed.get("quality")
        if isinstance(quality, list) and len(quality) > 0:
            quality = str(quality[0])
        elif quality:
            quality = str(quality)

        audio = parsed.get("audio")
        if isinstance(audio, list) and len(audio) > 0:
            audio = str(audio[0])
        elif audio:
            audio = str(audio)

        # 1. Fallback for Resolution
        if not resolution:
            lower_fn = filename.lower()
            if "2160" in lower_fn or "4k" in lower_fn:
                resolution = "2160p"
            elif "1080" in lower_fn:
                resolution = "1080p"
            elif "720" in lower_fn:
                resolution = "720p"
            elif "480" in lower_fn:
                resolution = "480p"
            elif "360" in lower_fn:
                resolution = "360p"

        # 2. Language Detection
        detected_langs: list[str] = []
        lower_fn = filename.lower()

        # Check for multi/dual
        if "multi" in lower_fn or "dual" in lower_fn:
            detected_langs.append("multi")
        else:
            # Check for configured languages
            for lang in self.app_config.supported_languages:
                keywords = self.LANGUAGE_KEYWORDS.get(lang, [lang])
                if any(kw in lower_fn for kw in keywords):
                    detected_langs.append(lang)

        languages_str: Optional[str] = (
            ",".join(detected_langs) if detected_langs else None
        )

        return {
            "title": title,
            "season": season,
            "episode": episode,
            "year": year,
            "resolution": resolution,
            "codec": codec,
            "quality": quality,
            "audio": audio,
            "languages": languages_str,
        }
