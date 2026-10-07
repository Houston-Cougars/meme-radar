import os, json
from datetime import datetime, timezone
from .apify_base import ApifyActorCollector
from ..models import SocialPost

def _dt(v):
    if not v: return datetime.now(timezone.utc)
    if isinstance(v,(int,float)):
        if v>10_000_000_000: v/=1000
        return datetime.fromtimestamp(v,tz=timezone.utc)
    try: return datetime.fromisoformat(str(v).replace("Z","+00:00"))
    except: return datetime.now(timezone.utc)

def _first(d,*keys,default=None):
    for k in keys:
        if isinstance(d,dict) and d.get(k) is not None: return d.get(k)
    return default

class InstagramApifyCollector(ApifyActorCollector):
    actor_env="APIFY_INSTAGRAM_ACTOR"
    actor_default="apify~instagram-api-scraper"
    def __init__(self,terms=None):
        super().__init__()
        if terms is None:
            try: terms=json.loads(os.getenv("INSTAGRAM_SEARCH_TERMS",'["viral","meme"]'))
            except: terms=["viral","meme"]
        self.terms=terms
        self.limit=int(os.getenv("SOCIAL_RESULTS_PER_QUERY","50"))
    async def collect(self):
        out=[]
        for term in self.terms:
            payload={"search":term,"searchType":"hashtag","searchLimit":1,"resultsType":"posts","resultsLimit":self.limit}
            for x in await self.run_actor(payload):
                pid=str(_first(x,"id","shortCode","shortcode",default=""))
                if not pid: continue
                owner=_first(x,"owner","author",default={}) or {}
                out.append(SocialPost(
                    platform="instagram",post_id=pid,created_at=_dt(_first(x,"timestamp","takenAt","taken_at_timestamp")),
                    author_id=str(_first(owner,"id",default=_first(x,"ownerId",default="")) or ""),
                    author_name=str(_first(owner,"username",default=_first(x,"ownerUsername","username",default="")) or ""),
                    text=str(_first(x,"caption","text","alt",default="") or ""),
                    url=str(_first(x,"url","postUrl","displayUrl",default="") or ""),
                    views=int(_first(x,"videoViewCount","videoPlayCount","views",default=0) or 0),
                    likes=int(_first(x,"likesCount","likeCount","likes",default=0) or 0),
                    comments=int(_first(x,"commentsCount","commentCount","comments",default=0) or 0),
                    shares=int(_first(x,"sharesCount","reshareCount","shares",default=0) or 0),
                    followers=int(_first(owner,"followersCount","followers",default=0) or 0),
                    media_url=str(_first(x,"displayUrl","videoUrl","thumbnailUrl",default="") or "") or None,
                ))
        return out
