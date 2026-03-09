from contextlib import asynccontextmanager
import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.redis_client import init_redis, close_redis
from app.api_client import init_http_client, close_http_client
from app.background_tasks import start_background_refresh
from app.routes.leaderboard import router as leaderboard_router
from app.routes.admin import router as admin_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: startup and shutdown"""
    await init_http_client()
    await init_redis()
    task = asyncio.create_task(start_background_refresh())
    logger.info("Application started, background refresh running")

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await close_http_client()
    await close_redis()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="MCSR Event Leaderboard",
    description="Leaderboard tracker for MCSR Ranked events",
    lifespan=lifespan,
)

app.include_router(leaderboard_router)
app.include_router(admin_router)

# Serve static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")
