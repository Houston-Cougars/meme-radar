import os
from .demo import DemoCollector
from .x_api import XCollector
from .tiktok_apify import TikTokApifyCollector
from .instagram_apify import InstagramApifyCollector
from .rss import RSSCollector

def build_collectors():
    out=[]
    if os.getenv("USE_DEMO_DATA","false").lower() in {"1","true","yes","on"}: out.append(DemoCollector())
    elif os.getenv("RSS_ENABLED","true").lower() in {"1","true","yes","on"}: out.append(RSSCollector())
    if os.getenv("ALLOW_PAID_PROVIDERS","false").lower() in {"1","true","yes","on"} and os.getenv("X_BEARER_TOKEN"): out.append(XCollector())
    if os.getenv("ALLOW_PAID_PROVIDERS","false").lower() in {"1","true","yes","on"} and os.getenv("APIFY_TOKEN"):
        if os.getenv("TIKTOK_PROVIDER","apify").lower()=="apify": out.append(TikTokApifyCollector())
        if os.getenv("INSTAGRAM_PROVIDER","apify").lower()=="apify": out.append(InstagramApifyCollector())
    return out
