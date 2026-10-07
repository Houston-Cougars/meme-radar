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

class TikTokApifyCollector(ApifyActorCollector):
    actor_env="APIFY_TIKTOK_ACTOR"
    actor_default="clockworks~tiktok-scraper"
    def __init__(self,terms=None):
        super().__init__()
        if terms is None:
            try: terms=json.loads(os.getenv("TIKTOK_SEARCH_TERMS",'["viral","meme"]'))
            except: terms=["viral","meme"]
        self.terms=terms
        self.limit=int(os.getenv("SOCIAL_RESULTS_PER_QUERY","50"))
    async def collect(self):
        out=[]
        for term in self.terms:
            payload={"searchQueries":[term],"resultsPerPage":self.limit,"shouldDownloadVideos":False}
            for x in await self.run_actor(payload):
                author=_first(x,"authorMeta","author",default={}) or {}
                stats=_first(x,"stats","statistics",default={}) or {}
                pid=str(_first(x,"id","videoId","aweme_id",default=""))
                if not pid: continue
                out.append(SocialPost(
                    platform="tiktok",post_id=pid,created_at=_dt(_first(x,"createTimeISO","createTime","create_time")),
                    author_id=str(_first(author,"id","uid","uniqueId",default="") or ""),
                    author_name=str(_first(author,"name","nickName","nickname","uniqueId",default="") or ""),
                    text=str(_first(x,"text","desc","description",default="") or ""),
                    url=str(_first(x,"webVideoUrl","url","videoUrl",default="") or ""),
                    views=int(_first(x,"playCount",default=_first(stats,"playCount","views",default=0)) or 0),
                    likes=int(_first(x,"diggCount",default=_first(stats,"diggCount","likes",default=0)) or 0),
                    comments=int(_first(x,"commentCount",default=_first(stats,"commentCount","comments",default=0)) or 0),
                    shares=int(_first(x,"shareCount",default=_first(stats,"shareCount","shares",default=0)) or 0),
                    followers=int(_first(author,"fans","fansCount","followers",default=0) or 0),
                    media_url=str(_first(x,"videoUrl","downloadAddr","webVideoUrl",default="") or "") or None,
                ))
        return out
