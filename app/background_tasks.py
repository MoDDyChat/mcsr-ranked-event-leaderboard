import asyncio
import logging
from typing import List, Dict, Any

from app.config import settings, load_players, load_casual_runs, load_event_dates
from app.api_client import fetch_player_elo
from app.models import PlayerStats
from app.redis_client import (
    cache_leaderboard,
    check_and_update_event_dates,
    get_player_uuid,
    set_player_uuid,
)
from app.match_fetcher import fetch_and_update_matches, compute_stats_from_matches

logger = logging.getLogger(__name__)

PLAYER_DELAY = 0.3  # Delay between players (seconds)


def merge_casual_runs(player: PlayerStats, config_runs: List[int]) -> PlayerStats:
    """Merge manual casual runs from config into player's casual stats."""
    if not config_runs:
        return player

    config_total_time = sum(config_runs)
    config_count = len(config_runs)
    config_best = min(config_runs)

    # PB: min between API and config
    if player.casual_personal_best is not None:
        new_pb = min(player.casual_personal_best, config_best)
    else:
        new_pb = config_best

    # Avg Time: (api_completion_time + config_total) / (api_completions + config_count)
    total_completions = player.casual_completions + config_count
    total_time = player.casual_completion_time + config_total_time
    new_avg = total_time / total_completions if total_completions > 0 else None

    # Wins: add config runs (all are wins)
    new_wins = player.casual_wins + config_count

    player.casual_personal_best = new_pb
    player.casual_average_time = new_avg
    player.casual_wins = new_wins
    player.casual_completions = total_completions
    player.casual_completion_time = total_time

    return player


async def refresh_leaderboard() -> None:
    """Fetch all player data and update cache using match history."""
    players = load_players()
    casual_runs = load_casual_runs()
    event_start, event_end = load_event_dates()
    results: List[Dict[str, Any]] = []

    logger.info(f"Refreshing leaderboard for {len(players)} players (event: {event_start} - {event_end})")

    # Invalidate match caches if event dates changed
    invalidated = await check_and_update_event_dates(event_start, event_end, players)
    if invalidated:
        logger.info("Event dates changed — all player match caches cleared")

    for nickname in players:
        try:
            # 1. Get elo and UUID from profile API
            profile = await fetch_player_elo(nickname)
            if profile is None:
                logger.warning(f"Skipping {nickname}: could not fetch profile")
                await asyncio.sleep(PLAYER_DELAY)
                continue

            display_name, uuid, elo = profile

            # Cache UUID for future use
            if uuid:
                cached_uuid = await get_player_uuid(nickname)
                if cached_uuid != uuid:
                    await set_player_uuid(nickname, uuid)

            await asyncio.sleep(PLAYER_DELAY)

            # 2. Fetch/update match history
            matches = await fetch_and_update_matches(
                nickname, uuid, event_start, event_end
            )

            # 3. Compute stats from event-period matches
            ranked_stats = compute_stats_from_matches(matches, match_type=2)
            casual_stats = compute_stats_from_matches(matches, match_type=1)

            # 4. Build PlayerStats
            player = PlayerStats(
                nickname=display_name,
                elo=elo,
                average_time=ranked_stats["average_time"],
                personal_best=ranked_stats["personal_best"],
                wins=ranked_stats["wins"],
                loses=ranked_stats["losses"],
                casual_average_time=casual_stats["average_time"],
                casual_personal_best=casual_stats["personal_best"],
                casual_wins=casual_stats["wins"],
                casual_loses=casual_stats["losses"],
                casual_completions=casual_stats["completions"],
                casual_completion_time=casual_stats["completion_time_total"],
            )

            # 5. Merge manual casual runs from config
            if nickname in casual_runs:
                player = merge_casual_runs(player, casual_runs[nickname])

            results.append(player.model_dump())

        except Exception as e:
            logger.error(f"Error processing {nickname}: {e}")

        await asyncio.sleep(PLAYER_DELAY)

    def sort_key(p):
        return (
            -p["elo"],
            p["personal_best"] if p["personal_best"] is not None else float("inf"),
            p["average_time"] if p["average_time"] is not None else float("inf"),
            -p["wins"],
            p["casual_personal_best"] if p["casual_personal_best"] is not None else float("inf"),
            p["casual_average_time"] if p["casual_average_time"] is not None else float("inf"),
            -(p["casual_wins"] + p["casual_loses"]),
        )
    results.sort(key=sort_key)

    await cache_leaderboard(results)
    logger.info(f"Leaderboard refreshed: {len(results)} players cached")


async def start_background_refresh() -> None:
    """Run refresh loop every configured interval"""
    await refresh_leaderboard()

    while True:
        await asyncio.sleep(settings.refresh_interval_seconds)
        try:
            await refresh_leaderboard()
        except Exception as e:
            logger.error(f"Background refresh error: {e}")
