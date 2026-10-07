import os, sqlite3
from datetime import datetime
from .models import SocialPost, MemeCandidate

POSTGRES = os.getenv("DATABASE_URL","").startswith(("postgres://","postgresql://"))

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
  platform TEXT NOT NULL, post_id TEXT NOT NULL, created_at TEXT NOT NULL, observed_at TEXT NOT NULL,
  author_id TEXT, author_name TEXT, text TEXT, url TEXT, views INTEGER DEFAULT 0, likes INTEGER DEFAULT 0,
  comments INTEGER DEFAULT 0, shares INTEGER DEFAULT 0, followers INTEGER DEFAULT 0,
  media_url TEXT, media_fingerprint TEXT, audio_fingerprint TEXT, ocr_text TEXT, transcript TEXT,
  PRIMARY KEY(platform, post_id, observed_at)
);
CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at);
CREATE INDEX IF NOT EXISTS idx_posts_platform ON posts(platform);
CREATE TABLE IF NOT EXISTS candidate_snapshots (
  observed_at TEXT NOT NULL, candidate_key TEXT NOT NULL, label TEXT NOT NULL, rank INTEGER,
  social_score REAL NOT NULL, crypto_saturation REAL NOT NULL, emergence_score REAL NOT NULL,
  velocity REAL NOT NULL, acceleration REAL NOT NULL, post_count INTEGER NOT NULL, creators INTEGER NOT NULL,
  platforms INTEGER NOT NULL, total_views INTEGER NOT NULL, total_engagement INTEGER NOT NULL,
  PRIMARY KEY(observed_at, candidate_key)
);
CREATE INDEX IF NOT EXISTS idx_candidate_key_time ON candidate_snapshots(candidate_key, observed_at DESC);
"""

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
  platform TEXT NOT NULL, post_id TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL, observed_at TIMESTAMPTZ NOT NULL,
  author_id TEXT, author_name TEXT, text TEXT, url TEXT, views BIGINT DEFAULT 0, likes BIGINT DEFAULT 0,
  comments BIGINT DEFAULT 0, shares BIGINT DEFAULT 0, followers BIGINT DEFAULT 0,
  media_url TEXT, media_fingerprint TEXT, audio_fingerprint TEXT, ocr_text TEXT, transcript TEXT,
  PRIMARY KEY(platform, post_id, observed_at)
);
CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at);
CREATE INDEX IF NOT EXISTS idx_posts_platform ON posts(platform);
CREATE TABLE IF NOT EXISTS candidate_snapshots (
  observed_at TIMESTAMPTZ NOT NULL, candidate_key TEXT NOT NULL, label TEXT NOT NULL, rank INTEGER,
  social_score DOUBLE PRECISION NOT NULL, crypto_saturation DOUBLE PRECISION NOT NULL,
  emergence_score DOUBLE PRECISION NOT NULL, velocity DOUBLE PRECISION NOT NULL,
  acceleration DOUBLE PRECISION NOT NULL, post_count INTEGER NOT NULL, creators INTEGER NOT NULL,
  platforms INTEGER NOT NULL, total_views BIGINT NOT NULL, total_engagement BIGINT NOT NULL,
  PRIMARY KEY(observed_at, candidate_key)
);
CREATE INDEX IF NOT EXISTS idx_candidate_key_time ON candidate_snapshots(candidate_key, observed_at DESC);
"""

def connect(path: str | None = None):
    url=os.getenv("DATABASE_URL","")
    if url.startswith(("postgres://","postgresql://")):
        import psycopg
        con=psycopg.connect(url)
        with con.cursor() as cur:
            cur.execute(POSTGRES_SCHEMA)
        con.commit()
        return con
    path=path or os.getenv("MEME_RADAR_DB","./meme_radar.db")
    con=sqlite3.connect(path)
    con.row_factory=sqlite3.Row
    con.executescript(SQLITE_SCHEMA)
    con.commit()
    return con

def _is_pg(con):
    return con.__class__.__module__.startswith("psycopg")

def save_posts(con, posts: list[SocialPost], observed_at: datetime):
    rows=[(p.platform,p.post_id,p.created_at,observed_at,p.author_id,p.author_name,p.text,p.url,
           p.views,p.likes,p.comments,p.shares,p.followers,p.media_url,p.media_fingerprint,
           p.audio_fingerprint,p.ocr_text,p.transcript) for p in posts]
    if not rows: return
    if _is_pg(con):
        with con.cursor() as cur:
            cur.executemany("""INSERT INTO posts
            (platform,post_id,created_at,observed_at,author_id,author_name,text,url,views,likes,comments,shares,followers,
             media_url,media_fingerprint,audio_fingerprint,ocr_text,transcript)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT DO NOTHING""", rows)
    else:
        rows=[tuple(x.isoformat() if hasattr(x,"isoformat") else x for x in r) for r in rows]
        con.executemany("""INSERT OR IGNORE INTO posts
        (platform,post_id,created_at,observed_at,author_id,author_name,text,url,views,likes,comments,shares,followers,
         media_url,media_fingerprint,audio_fingerprint,ocr_text,transcript)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", rows)
    con.commit()

def load_previous_candidate(con,key:str):
    if _is_pg(con):
        with con.cursor() as cur:
            cur.execute("""SELECT observed_at,candidate_key,label,rank,social_score,crypto_saturation,emergence_score,
                           velocity,acceleration,post_count,creators,platforms,total_views,total_engagement
                           FROM candidate_snapshots WHERE candidate_key=%s ORDER BY observed_at DESC LIMIT 1""",(key,))
            row=cur.fetchone()
            if not row: return None
            cols=[d.name for d in cur.description]
            return dict(zip(cols,row))
    row=con.execute("""SELECT * FROM candidate_snapshots WHERE candidate_key=? ORDER BY observed_at DESC LIMIT 1""",(key,)).fetchone()
    return dict(row) if row else None

def save_candidate_snapshots(con,candidates:list[MemeCandidate],observed_at:datetime):
    rows=[(observed_at,c.key,c.label,c.rank,c.social_score,c.crypto_saturation,c.emergence_score,c.velocity,c.acceleration,
           c.post_count,c.creators,c.platforms,c.total_views,c.total_engagement) for c in candidates]
    if not rows: return
    if _is_pg(con):
        with con.cursor() as cur:
            cur.executemany("""INSERT INTO candidate_snapshots
            (observed_at,candidate_key,label,rank,social_score,crypto_saturation,emergence_score,velocity,acceleration,
             post_count,creators,platforms,total_views,total_engagement)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",rows)
    else:
        rows=[tuple(x.isoformat() if hasattr(x,"isoformat") else x for x in r) for r in rows]
        con.executemany("""INSERT OR REPLACE INTO candidate_snapshots
        (observed_at,candidate_key,label,rank,social_score,crypto_saturation,emergence_score,velocity,acceleration,
         post_count,creators,platforms,total_views,total_engagement)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",rows)
    con.commit()
