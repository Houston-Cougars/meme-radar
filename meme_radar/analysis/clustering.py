import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from ..models import SocialPost, MemeCandidate

STOP = {
    "the","a","an","and","or","to","of","is","it","this","that","for","on","in",
    "with","bro","what","who","why","how","meme","viral","everywhere","happening",
    "video","lol","lmao","omg","just","from","about","have","has","was","are",
}

def text_blob(p: SocialPost) -> str:
    return " ".join(x for x in [p.text, p.ocr_text or "", p.transcript or ""] if x)

def normalize_key(text: str) -> str:
    words = re.findall(r"[a-zA-Z0-9$]+", text.lower())
    words = [w for w in words if len(w) > 2 and w not in STOP and not w.startswith("http")]
    return " ".join(words[:5]) or "unknown"

def make_label(key: str) -> str:
    return " ".join(x.capitalize() for x in key.replace("$", "").split())

def similarity(a: str, b: str) -> float:
    aset, bset = set(a.split()), set(b.split())
    jaccard = len(aset & bset) / max(1, len(aset | bset))
    seq = SequenceMatcher(None, a, b).ratio()
    return max(jaccard, seq)

def canonicalize_keys(keys: list[str], threshold: float = 0.72) -> dict[str, str]:
    canonical: list[str] = []
    mapping: dict[str, str] = {}
    for key in sorted(keys, key=len):
        match = next((c for c in canonical if similarity(key, c) >= threshold), None)
        if match:
            mapping[key] = match
        else:
            canonical.append(key)
            mapping[key] = key
    return mapping

def cluster(posts: list[SocialPost], now: datetime | None = None) -> list[MemeCandidate]:
    now = now or datetime.now(timezone.utc)
    raw_keys = [normalize_key(text_blob(p)) for p in posts]
    mapping = canonicalize_keys(list(dict.fromkeys(raw_keys)))
    buckets = defaultdict(list)

    for p, raw_key in zip(posts, raw_keys):
        # Exact media fingerprint wins over text grouping when available.
        key = f"media:{p.media_fingerprint}" if p.media_fingerprint else mapping[raw_key]
        buckets[key].append(p)

    candidates = []
    for key, group in buckets.items():
        if len(group) < 3:
            continue
        first = min(p.created_at for p in group)
        last = max(p.created_at for p in group)
        creators = len({(p.platform, p.author_id) for p in group})
        platforms = len({p.platform for p in group})
        recent = [p for p in group if p.created_at >= now - timedelta(hours=1)]
        prior = [p for p in group if now - timedelta(hours=2) <= p.created_at < now - timedelta(hours=1)]
        eng = lambda p: p.likes + 2*p.comments + 3*p.shares
        raw_label = normalize_key(text_blob(group[0])) if key.startswith("media:") else key
        candidates.append(MemeCandidate(
            key=key,
            label=make_label(raw_label),
            first_seen=first,
            last_seen=last,
            post_count=len(group),
            creators=creators,
            platforms=platforms,
            total_views=sum(p.views for p in group),
            total_engagement=sum(eng(p) for p in group),
            recent_engagement=sum(eng(p) for p in recent),
            prior_engagement=sum(eng(p) for p in prior),
            remix_count=max(0, len(group)-1),
        ))
    return candidates
