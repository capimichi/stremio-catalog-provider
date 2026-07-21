from typing import Any, Optional
import PTN

class TorrentParserService:
    """Service to parse media filenames using PTN (Python Torrent Name parser)."""

    def parse_filename(self, filename: str) -> dict[str, Any]:
        """Parses a filename to extract title, season, episode and year."""
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

        return {
            "title": title,
            "season": season,
            "episode": episode,
            "year": year
        }
