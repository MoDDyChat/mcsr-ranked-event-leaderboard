import logging
import yaml
from datetime import datetime, timezone
from pydantic_settings import BaseSettings
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    redis_url: str = "redis://redis:6379"
    refresh_interval_seconds: int = 60
    mcsr_api_base: str = "https://mcsrranked.com/api"
    admin_api_key: str = ""

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def _load_config() -> dict:
    """Load and return raw config.yaml"""
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def load_players() -> List[str]:
    """Load player nicknames from config.yaml"""
    return _load_config().get("players", [])


def parse_time(time_str: str) -> int:
    """Parse MM:SS.mmm format to milliseconds.

    Examples: "11:42.960" -> 702960, "9:10.500" -> 550500
    """
    try:
        parts = time_str.split(":")
        minutes = int(parts[0])
        sec_parts = parts[1].split(".")
        seconds = int(sec_parts[0])
        millis = int(sec_parts[1]) if len(sec_parts) > 1 else 0
        return minutes * 60000 + seconds * 1000 + millis
    except (ValueError, IndexError):
        logger.warning(f"Invalid time format: {time_str}")
        return 0


def load_casual_runs() -> Dict[str, List[int]]:
    """Load manual casual runs from config.yaml, parsed to milliseconds.

    Config format:
        casual_runs:
          PlayerName:
            - "11:42.960"
            - "9:10.500"

    Returns: {"PlayerName": [702960, 550500]}
    """
    raw = _load_config().get("casual_runs", {})
    if not raw:
        return {}

    result: Dict[str, List[int]] = {}
    for nickname, runs in raw.items():
        parsed = [parse_time(str(r)) for r in runs]
        # Filter out invalid (0) values
        parsed = [t for t in parsed if t > 0]
        if parsed:
            result[nickname] = parsed
    return result


def add_player(nickname: str) -> bool:
    """Add a player to config.yaml. Returns False if already exists."""
    config = _load_config()
    players = config.get("players", [])
    if nickname in players:
        return False
    players.append(nickname)
    config["players"] = players
    with open("config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    return True


def remove_player(nickname: str) -> bool:
    """Remove a player from config.yaml. Returns False if not found."""
    config = _load_config()
    players = config.get("players", [])
    if nickname not in players:
        return False
    players.remove(nickname)
    config["players"] = players
    with open("config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    return True


def load_event_dates() -> Tuple[Optional[int], Optional[int]]:
    """Load event_start and event_end from config.yaml as Unix timestamps.

    event_end is inclusive of the entire day (midnight of the next day).
    """
    config = _load_config()
    start_str = config.get("event_start")
    end_str = config.get("event_end")

    start_ts = None
    end_ts = None
    if start_str:
        dt = datetime.strptime(str(start_str), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        start_ts = int(dt.timestamp())
    if end_str:
        dt = datetime.strptime(str(end_str), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_ts = int(dt.timestamp()) + 86400  # end of day inclusive
    return start_ts, end_ts


settings = get_settings()
