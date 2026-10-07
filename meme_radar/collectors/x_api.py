import os
from datetime import datetime
import httpx
from .base import Collector
from ..models import SocialPost

class XCollector(Collector):
    """
    Minimal X recent-search adapter.
    Configure queries around broad meme discovery terms plus dynamic terms generated
    from prior candidate clusters. Production deployments should use the official
    SDK/streaming product appropriate to the account tier.
    """
    def __init__(self, queries: list[str] | None = None):
        self.token = os.getenv("X_BEARER_TOKEN", "")
        self.queries = queries or [
            '"went viral" -is:retweet lang:en',
            'meme -is:retweet lang:en',
            '"who is" meme -is:retweet lang:en',
        ]

    async def collect(self) -> list[SocialPost]:
        if not self.token:
            return []
        headers = {"Authorization": f"Bearer {self.token}"}
        posts: list[SocialPost] = []
        async with httpx.AsyncClient(timeout=30) as client:
            for q in self.queries:
                r = await client.get(
                    "https://api.x.com/2/tweets/search/recent",
                    headers=headers,
                    params={
                        "query": q,
                        "max_results": 100,
                        "tweet.fields": "created_at,author_id,public_metrics",
                    },
                )
                r.raise_for_status()
                for t in r.json().get("data", []):
                    m = t.get("public_metrics", {})
                    posts.append(SocialPost(
                        platform="x",
                        post_id=t["id"],
                        created_at=datetime.fromisoformat(t["created_at"].replace("Z","+00:00")),
                        author_id=t.get("author_id",""),
                        author_name="",
                        text=t.get("text",""),
                        url=f"https://x.com/i/web/status/{t['id']}",
                        likes=m.get("like_count", 0),
                        comments=m.get("reply_count", 0),
                        shares=m.get("retweet_count", 0) + m.get("quote_count", 0),
                    ))
        return posts
