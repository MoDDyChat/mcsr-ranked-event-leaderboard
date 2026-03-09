from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.redis_client import get_cached_leaderboard
from app.models import LeaderboardResponse

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main HTML page"""
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/api/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard():
    """Return cached leaderboard data as JSON"""
    players, last_updated = await get_cached_leaderboard()
    return LeaderboardResponse(players=players, last_updated=last_updated)
