import os, sqlite3
from dotenv import load_dotenv
load_dotenv()
if not os.getenv("DATABASE_URL","").startswith(("postgres://","postgresql://")):
    raise SystemExit("Set DATABASE_URL to Postgres first.")
from meme_radar.db import connect
src=sqlite3.connect(os.getenv("MEME_RADAR_DB","./meme_radar.db")); src.row_factory=sqlite3.Row
dst=connect()
with dst.cursor() as cur:
    for row in src.execute("SELECT * FROM posts"):
        vals=tuple(row)
        cur.execute("""INSERT INTO posts(platform,post_id,created_at,observed_at,author_id,author_name,text,url,views,likes,comments,shares,followers,media_url,media_fingerprint,audio_fingerprint,ocr_text,transcript)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",vals)
    for row in src.execute("SELECT * FROM candidate_snapshots"):
        vals=tuple(row)
        cur.execute("""INSERT INTO candidate_snapshots(observed_at,candidate_key,label,rank,social_score,crypto_saturation,emergence_score,velocity,acceleration,post_count,creators,platforms,total_views,total_engagement)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",vals)
dst.commit()
print("Migration complete.")
