import asyncio
import httpx
import logging
from typing import Optional, Tuple, List, Dict, Any

from app.config import settings
from app.models import PlayerStats

logger = logging.getLogger(__name__)

_client: Optional[httpx.AsyncClient] = None


async def init_http_client() -> None:
    global _client
    _client = httpx.AsyncClient(timeout=15.0)


async def close_http_client() -> None:
    global _client
    if _client:
        await _client.aclose()
        _client = None


def get_http_client() -> httpx.AsyncClient:
    if _client is None:
        raise RuntimeError("HTTP client not initialized.")
    return _client


async def api_get_with_retry(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
) -> Optional[httpx.Response]:
    """GET request with retry on 429 (rate limit) using exponential backoff."""
    client = get_http_client()
    for attempt in range(max_retries):
        try:
            response = await client.get(url, params=params)
            if response.status_code == 429:
                wait = 2 ** attempt
                logger.warning(f"Rate limited on {url}, waiting {wait}s (attempt {attempt + 1})")
                await asyncio.sleep(wait)
                continue
            return response
        except Exception as e:
            logger.error(f"HTTP error on {url}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
            else:
                return None
    return None


async def fetch_player_elo(nickname: str) -> Optional[Tuple[str, str, int]]:
    """Fetch player's display name, UUID, and elo from profile API.

    Returns (nickname, uuid, elo) or None on error.
    """
    url = f"{settings.mcsr_api_base}/users/{nickname}"
    response = await api_get_with_retry(url)

    if response is None or response.status_code != 200:
        logger.warning(f"API error fetching elo for {nickname}")
        return None

    try:
        json_data = response.json()
        if json_data.get("status") != "success":
            return None

        data = json_data.get("data", {})
        return (
            data.get("nickname") or nickname,
            data.get("uuid", ""),
            data.get("eloRate") or 0,
        )
    except Exception as e:
        logger.error(f"Error parsing profile for {nickname}: {e}")
        return None


async def fetch_matches_page(
    nickname: str,
    count: int = 100,
    season: int = 10,
    sort: str = "newest",
    after: Optional[int] = None,
) -> Optional[List[Dict[str, Any]]]:
    """Fetch a single page of match history for a player."""
    url = f"{settings.mcsr_api_base}/users/{nickname}/matches"
    params: Dict[str, Any] = {
        "count": count,
        "season": season,
        "sort": sort,
    }
    if after is not None:
        params["after"] = after

    response = await api_get_with_retry(url, params=params)

    if response is None or response.status_code != 200:
        logger.warning(f"API error fetching matches for {nickname}")
        return None

    try:
        json_data = response.json()
        if json_data.get("status") != "success":
            return None
        return json_data.get("data", [])
    except Exception as e:
        logger.error(f"Error parsing matches for {nickname}: {e}")
        return None


async def fetch_player_data(nickname: str) -> Optional[PlayerStats]:
    """Fetch and transform player data from MCSR Ranked API (legacy — season summary)."""
    url = f"{settings.mcsr_api_base}/users/{nickname}"
    response = await api_get_with_retry(url)

    if response is None or response.status_code != 200:
        logger.warning(f"API error for {nickname}: status {getattr(response, 'status_code', 'N/A')}")
        return None

    try:
        json_data = response.json()

        if json_data.get("status") != "success":
            logger.warning(f"API returned non-success for {nickname}")
            return None

        data = json_data.get("data", {})
        stats = data.get("statistics", {}).get("season", {})

        r_completions = stats.get("completions", {}).get("ranked", 0) or 0
        r_completion_time = stats.get("completionTime", {}).get("ranked", 0) or 0
        r_average_time = (r_completion_time / r_completions) if r_completions > 0 else None
        r_personal_best = stats.get("bestTime", {}).get("ranked")

        c_completions = stats.get("completions", {}).get("casual", 0) or 0
        c_completion_time = stats.get("completionTime", {}).get("casual", 0) or 0
        c_average_time = (c_completion_time / c_completions) if c_completions > 0 else None
        c_personal_best = stats.get("bestTime", {}).get("casual")

        return PlayerStats(
            nickname=data.get("nickname") or nickname,
            elo=data.get("eloRate") or 0,
            average_time=r_average_time,
            personal_best=r_personal_best,
            wins=stats.get("wins", {}).get("ranked") or 0,
            loses=stats.get("loses", {}).get("ranked") or 0,
            casual_average_time=c_average_time,
            casual_personal_best=c_personal_best,
            casual_wins=stats.get("wins", {}).get("casual") or 0,
            casual_loses=stats.get("loses", {}).get("casual") or 0,
            casual_completions=c_completions,
            casual_completion_time=c_completion_time,
        )
    except Exception as e:
        logger.error(f"Error fetching {nickname}: {e}")
        return None
