from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from app.config import settings, load_players, add_player, remove_player

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _check_auth(x_api_key: str) -> None:
    """Verify API key."""
    if not settings.admin_api_key:
        raise HTTPException(status_code=503, detail="Admin API key not configured")
    if x_api_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


class PlayerRequest(BaseModel):
    nickname: str


@router.post("/players")
async def api_add_player(
    body: PlayerRequest,
    x_api_key: str = Header(),
):
    """Add a player to the tracking list."""
    _check_auth(x_api_key)

    if add_player(body.nickname):
        logger.info(f"Player added: {body.nickname}")
        return {"status": "added", "nickname": body.nickname}
    return {"status": "exists", "nickname": body.nickname}


@router.delete("/players")
async def api_remove_player(
    body: PlayerRequest,
    x_api_key: str = Header(),
):
    """Remove a player from the tracking list."""
    _check_auth(x_api_key)

    if remove_player(body.nickname):
        logger.info(f"Player removed: {body.nickname}")
        return {"status": "removed", "nickname": body.nickname}
    raise HTTPException(status_code=404, detail="Player not found")


@router.get("/players")
async def api_list_players(
    x_api_key: str = Header(),
):
    """List all tracked players."""
    _check_auth(x_api_key)
    return {"players": load_players()}
