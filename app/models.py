from pydantic import BaseModel
from typing import Optional, List


class PlayerStats(BaseModel):
    nickname: str
    elo: int
    # Ranked
    average_time: Optional[float] = None
    personal_best: Optional[int] = None
    wins: int = 0
    loses: int = 0
    # Casual
    casual_average_time: Optional[float] = None
    casual_personal_best: Optional[int] = None
    casual_wins: int = 0
    casual_loses: int = 0
    # Raw casual data (for merging with config runs)
    casual_completions: int = 0
    casual_completion_time: float = 0


class LeaderboardResponse(BaseModel):
    players: List[PlayerStats]
    last_updated: str
