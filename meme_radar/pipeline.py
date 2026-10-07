from datetime import datetime, timezone
from .analysis.clustering import cluster
from .analysis.scoring import score, rescore_after_crypto
from .analysis.dexscreener import DexScreenerClient
from .analysis.change_detection import annotate_changes
from .db import connect, save_posts, save_candidate_snapshots

async def run_pipeline(collectors):
    now = datetime.now(timezone.utc)
    posts = []
    successful_collectors = 0
    for collector in collectors:
        try:
            posts.extend(await collector.collect())
            successful_collectors += 1
        except Exception as exc:
            print(f"collector error {collector.__class__.__name__}: {type(exc).__name__}")

    if not successful_collectors:
        raise RuntimeError("All collectors failed; no report will be delivered.")
    # Search queries can return the same post. Count each platform/post only once.
    posts = list({(p.platform, p.post_id): p for p in posts}.values())

    con = connect()
    try:
        save_posts(con, posts, now)
        candidates = [score(c) for c in cluster(posts, now)]
        dex = DexScreenerClient()
        for c in sorted(candidates, key=lambda x: x.social_score, reverse=True)[:20]:
            try:
                c.token_matches = await dex.search(c.label)
            except Exception as exc:
                print(f"dex lookup error for {c.label}: {type(exc).__name__}")
                c.token_matches = []
            rescore_after_crypto(c)
        candidates = annotate_changes(con, candidates)
        save_candidate_snapshots(con, candidates, now)
    finally:
        con.close()
    return now, posts, candidates
