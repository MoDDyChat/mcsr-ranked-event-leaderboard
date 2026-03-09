import redis.asyncio as redis
import json
from datetime import datetime
from typing import Tuple, List, Dict, Any, Optional

from app.config import settings

redis_client: Optional[redis.Redis] = None

LEADERBOARD_KEY = "leaderboard:data"
LAST_UPDATE_KEY = "leaderboard:last_update"
EVENT_DATES_KEY = "event:dates"


async def init_redis() -> None:
    """Initialize Redis connection"""
    global redis_client
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)


async def close_redis() -> None:
    """Close Redis connection"""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


async def cache_leaderboard(players: List[Dict[str, Any]]) -> None:
    """Store the entire leaderboard as a single JSON blob"""
    if redis_client is None:
        return
    await redis_client.set(LEADERBOARD_KEY, json.dumps(players))
    await redis_client.set(LAST_UPDATE_KEY, datetime.utcnow().isoformat() + "Z")


async def get_cached_leaderboard() -> Tuple[List[Dict[str, Any]], str]:
    """Retrieve cached leaderboard data"""
    if redis_client is None:
        return [], "Never"

    data = await redis_client.get(LEADERBOARD_KEY)
    last_update = await redis_client.get(LAST_UPDATE_KEY)

    if data:
        return json.loads(data), last_update or "Never"
    return [], "Never"


# --- Per-player match cache ---

def _player_key(nickname: str, suffix: str) -> str:
    return f"player:{nickname}:{suffix}"


async def get_player_matches(nickname: str) -> List[Dict[str, Any]]:
    if redis_client is None:
        return []
    data = await redis_client.get(_player_key(nickname, "matches"))
    if data:
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return []
    return []


async def set_player_matches(nickname: str, matches: List[Dict[str, Any]]) -> None:
    if redis_client is None:
        return
    await redis_client.set(_player_key(nickname, "matches"), json.dumps(matches))


async def get_player_last_match_id(nickname: str) -> Optional[int]:
    if redis_client is None:
        return None
    val = await redis_client.get(_player_key(nickname, "last_match_id"))
    if val is not None:
        return int(val)
    return None


async def set_player_last_match_id(nickname: str, match_id: int) -> None:
    if redis_client is None:
        return
    await redis_client.set(_player_key(nickname, "last_match_id"), str(match_id))


async def get_player_uuid(nickname: str) -> Optional[str]:
    if redis_client is None:
        return None
    return await redis_client.get(_player_key(nickname, "uuid"))


async def set_player_uuid(nickname: str, uuid: str) -> None:
    if redis_client is None:
        return
    await redis_client.set(_player_key(nickname, "uuid"), uuid)


# --- Event dates change detection ---

async def check_and_update_event_dates(
    event_start: Optional[int], event_end: Optional[int], players: List[str]
) -> bool:
    """Check if event dates changed since last run. If so, clear all player match caches.

    Returns True if caches were invalidated.
    """
    if redis_client is None:
        return False

    # Bump cache_version when match processing logic changes to force re-fetch
    current = json.dumps({"start": event_start, "end": event_end, "v": 3})
    stored = await redis_client.get(EVENT_DATES_KEY)

    if stored == current:
        return False

    # Dates changed — clear per-player match caches
    for nickname in players:
        await redis_client.delete(_player_key(nickname, "matches"))
        await redis_client.delete(_player_key(nickname, "last_match_id"))

    await redis_client.set(EVENT_DATES_KEY, current)
    return True
