from datetime import datetime, timedelta, timezone
from .base import Collector
from ..models import SocialPost

class DemoCollector(Collector):
    """Synthetic data so the entire scoring/report pipeline can be tested without API keys."""
    async def collect(self) -> list[SocialPost]:
        now = datetime.now(timezone.utc)
        out = []
        specs = [
            ("x", "Jean Phil", 32, 48000, 7000, 900),
            ("tiktok", "Jean Phil", 20, 410000, 31000, 3900),
            ("instagram", "Jean Phil", 9, 160000, 12000, 1200),
            ("x", "CyberLeek", 23, 75000, 10500, 1200),
            ("tiktok", "CyberLeek", 8, 100000, 11000, 700),
            ("x", "Parking Lot Wizard", 7, 12000, 800, 80),
        ]
        n = 0
        for platform, phrase, count, views, likes, shares in specs:
            for i in range(count):
                n += 1
                out.append(SocialPost(
                    platform=platform,
                    post_id=f"demo-{n}",
                    created_at=now - timedelta(minutes=(i % 55)),
                    author_id=f"{platform}-author-{i}",
                    author_name=f"user{i}",
                    text=f"{phrase} {['bro knows','this is everywhere','what is happening','meme'][i%4]}",
                    url="",
                    views=max(1, views - i*317),
                    likes=max(1, likes - i*41),
                    comments=max(1, likes//20 - i),
                    shares=max(1, shares - i*5),
                    followers=500 + i*73
                ))
        return out
