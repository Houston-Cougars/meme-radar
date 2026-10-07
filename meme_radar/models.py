from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class SocialPost:
    platform: str
    post_id: str
    created_at: datetime
    author_id: str
    author_name: str
    text: str
    url: str = ""
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    followers: int = 0
    media_url: Optional[str] = None
    media_fingerprint: Optional[str] = None
    audio_fingerprint: Optional[str] = None
    ocr_text: Optional[str] = None
    transcript: Optional[str] = None

    @property
    def engagement(self) -> int:
        return self.likes + self.comments * 2 + self.shares * 3

@dataclass
class MemeCandidate:
    key: str
    label: str
    first_seen: datetime
    last_seen: datetime
    post_count: int
    creators: int
    platforms: int
    total_views: int
    total_engagement: int
    recent_engagement: int
    prior_engagement: int
    remix_count: int
    velocity: float = 0.0
    acceleration: float = 0.0
    social_score: float = 0.0
    crypto_saturation: float = 0.0
    emergence_score: float = 0.0
    token_matches: list[dict] = field(default_factory=list)
    rank: Optional[int] = None
    prior_rank: Optional[int] = None
    prior_emergence_score: Optional[float] = None
    score_delta: float = 0.0
    status: str = "NEW"
