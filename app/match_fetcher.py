import asyncio
import logging
from typing import Optional, List, Dict, Any, Tuple

from app.api_client import fetch_matches_page
from app.redis_client import (
    get_player_matches,
    set_player_matches,
    get_player_last_match_id,
    set_player_last_match_id,
)

logger = logging.getLogger(__name__)

MAX_PAGES = 20  
PAGE_DELAY = 0.2 # seconds


def _process_match(match: Dict[str, Any], player_uuid: str) -> Dict[str, Any]:
    """Extract slim match dict for caching."""
    result = match.get("result") or {}
    won = result.get("uuid") == player_uuid
    forfeited = match.get("forfeited", False)

    completion_time = None
    if won and not forfeited and result.get("time"):
        completion_time = result["time"]

    return {
        "id": match["id"],
        "date": match["date"],
        "type": match.get("type"),
        "won": won,
        "forfeited": forfeited,
        "completion_time": completion_time,
    }


def _find_player_uuid(match: Dict[str, Any], nickname: str) -> Optional[str]:
    """Extract player UUID from a match's players array by nickname (case-insensitive)."""
    for player in match.get("players", []):
        if player.get("nickname", "").lower() == nickname.lower():
            return player["uuid"]
    return None


async def fetch_and_update_matches(
    nickname: str,
    player_uuid: str,
    event_start: Optional[int],
    event_end: Optional[int],
) -> List[Dict[str, Any]]:
    """Fetch new matches for a player and update Redis cache.

    First run: pages backward from newest until hitting matches before event_start.
    Subsequent runs: fetches only matches newer than last_match_id.

    Returns the full list of cached event-period matches.
    """
    last_match_id = await get_player_last_match_id(nickname)

    if last_match_id is not None:
        new_matches = await _fetch_incremental(nickname, player_uuid, event_start, event_end, last_match_id)
        if new_matches:
            existing = await get_player_matches(nickname)
            existing_ids = {m["id"] for m in existing}
            for m in new_matches:
                if m["id"] not in existing_ids:
                    existing.append(m)
            await set_player_matches(nickname, existing)
            # Update last_match_id to the newest
            newest_id = max(m["id"] for m in existing)
            await set_player_last_match_id(nickname, newest_id)
            return existing
        return await get_player_matches(nickname)
    else:
        matches = await _fetch_first_run(nickname, player_uuid, event_start, event_end)
        if matches:
            await set_player_matches(nickname, matches)
            newest_id = max(m["id"] for m in matches)
            await set_player_last_match_id(nickname, newest_id)
        return matches


async def _fetch_first_run(
    nickname: str,
    player_uuid: str,
    event_start: Optional[int],
    event_end: Optional[int],
) -> List[Dict[str, Any]]:
    """First-time fetch: page backward from newest matches until before event_start."""
    collected: List[Dict[str, Any]] = []
    after_id: Optional[int] = None

    for page_num in range(MAX_PAGES):
        page = await fetch_matches_page(
            nickname, count=100, season=10, sort="newest", after=after_id
        )
        if not page:
            break

        reached_start = False
        for match in page:
            match_date = match.get("date", 0)

            if event_start is not None and match_date < event_start:
                reached_start = True
                break

            if event_end is not None and match_date >= event_end:
                continue

            match_type = match.get("type")
            if match_type not in (1, 2):
                continue

            slim = _process_match(match, player_uuid)
            collected.append(slim)

        if reached_start:
            break

        # If page was full, continue paginating
        if len(page) < 100:
            break

        after_id = page[-1]["id"]
        await asyncio.sleep(PAGE_DELAY)

    logger.info(f"First run for {nickname}: collected {len(collected)} event matches")
    return collected


async def _fetch_incremental(
    nickname: str,
    player_uuid: str,
    event_start: Optional[int],
    event_end: Optional[int],
    last_match_id: int,
) -> List[Dict[str, Any]]:
    """Incremental fetch: get matches newer than last_match_id.

    Uses sort=newest and stops when hitting a known match (id <= last_match_id).
    """
    collected: List[Dict[str, Any]] = []
    after_id: Optional[int] = None

    for page_num in range(MAX_PAGES):
        page = await fetch_matches_page(
            nickname, count=100, season=10, sort="newest", after=after_id
        )
        if not page:
            break

        done = False
        for match in page:
            if match["id"] <= last_match_id:
                done = True
                break

            match_date = match.get("date", 0)

            if event_end is not None and match_date >= event_end:
                continue

            if event_start is not None and match_date < event_start:
                done = True
                break

            match_type = match.get("type")
            if match_type not in (1, 2):
                continue

            slim = _process_match(match, player_uuid)
            collected.append(slim)

        if done:
            break

        if len(page) < 100:
            break

        after_id = page[-1]["id"]
        await asyncio.sleep(PAGE_DELAY)

    if collected:
        logger.info(f"Incremental for {nickname}: {len(collected)} new event matches")
    return collected


def compute_stats_from_matches(matches: List[Dict[str, Any]], match_type: int) -> Dict[str, Any]:
    """Compute wins, losses, PB, and average time from cached match data.

    Args:
        matches: List of slim match dicts.
        match_type: 2 for ranked, 1 for casual.
    """
    wins = 0
    losses = 0
    completion_times: List[int] = []

    for m in matches:
        if m.get("type") != match_type:
            continue
        if m["won"]:
            wins += 1
            if not m["forfeited"] and m["completion_time"]:
                completion_times.append(m["completion_time"])
        else:
            losses += 1

    pb = min(completion_times) if completion_times else None
    avg_time = sum(completion_times) / len(completion_times) if completion_times else None

    return {
        "wins": wins,
        "losses": losses,
        "personal_best": pb,
        "average_time": avg_time,
        "completions": len(completion_times),
        "completion_time_total": sum(completion_times) if completion_times else 0,
    }
