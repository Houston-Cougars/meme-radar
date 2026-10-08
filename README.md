# Meme Radar V4

## Windows desktop app

Run MemeRadar.exe for a full-screen dashboard with automatic public-feed collection, local SQLite history, headline filtering, news searches, source links, and source/interval settings. No Python installation is required for the packaged executable. Data lives in MemeRadar-data beside the executable. The app collects while open; F11 toggles full screen and Escape leaves full screen. Desktop mode never uses paid providers or hosted Postgres. Feed availability and RSS scoring limitations still apply. Build from source with Build-Windows.ps1.


## Free local mode (default)

Run `./Run-Local.ps1` on Windows with Python 3.12+ installed. It creates a local virtual environment and copies the blank-secret configuration to `.env`. SQLite history stays in `meme_radar.db` and reports stay in `reports/`. No Render account, hosted Postgres, Apify token, or X account is required.

Default live sources are public Reddit RSS/Atom feeds from r/memes and r/dankmemes. Configure other public feeds with `RSS_FEEDS`. Feed access can be blocked or rate limited and has not been verified live. RSS provides titles, authors, links, and dates but no reliable engagement metrics; V4 engagement and cross-platform breakout scoring is limited in this mode. This does not reproduce TikTok/Instagram discovery. If all feeds fail, the run fails instead of substituting demo posts.

Keep `ALLOW_PAID_PROVIDERS=false` to prevent Apify and X from running even when credentials are present. Set `USE_DEMO_DATA=true` only for synthetic testing. Discord remains optional through a webhook in `.env`.

Run `python run_daemon.py` from the activated virtual environment to repeat hourly while your computer is awake. Local electricity and internet usage still apply. No scheduled task has been installed. Render configuration below is retained as an optional paid hosting alternative, not the default.


Hourly meme discovery using TikTok and Instagram via Apify, optional X recent search, text clustering, social scoring, DEX Screener checks, and Discord delivery. Postgres retains post observations and candidate scores/ranks across Render runs. SQLite remains available for local use.

## Local setup (Python 3.12+)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

For a first run without provider credentials, set `USE_DEMO_DATA=true` in `.env`, then run `python run_once.py`. Leave both Discord URLs blank to avoid delivery. Markdown and JSON reports are written to `reports/`, including `latest.md`. The demo still makes public DEX Screener requests; tests mock external requests.

For optional Apify collection, set `ALLOW_PAID_PROVIDERS=true` and `USE_DEMO_DATA=false` and supply `APIFY_TOKEN` in your local `.env` or hosting secret environment. Both Apify adapters are enabled by default. Their actor IDs and search terms are configurable in `.env.example`. Start with `SOCIAL_RESULTS_PER_QUERY=25`: every term starts a separate actor run, and Apify charges for collection. Instagram searches hashtags; TikTok searches keywords. Actor output and search coverage can vary over time.

Set `DISCORD_WEBHOOK_URL` for the hourly digest. Set `DISCORD_ALERT_WEBHOOK_URL` for a separate breakout channel, or leave it blank to reuse the digest channel. `X_BEARER_TOKEN` is optional and requires X API recent-search access. Never commit `.env` or credentials.

## Render deployment

The root `render.yaml` prepares:

- `meme-radar-hourly`: Docker cron, `0 * * * *`, running `python run_once.py`.
- `meme-radar-postgres`: managed Postgres in the same region, linked through `DATABASE_URL` using its internal connection string.
- Four user-provided secrets marked `sync: false`: `APIFY_TOKEN`, `DISCORD_WEBHOOK_URL`, `DISCORD_ALERT_WEBHOOK_URL`, and optional `X_BEARER_TOKEN`.

[Create the Render Blueprint](https://dashboard.render.com/blueprint/new?repo=https://github.com/Houston-Cougars/meme-radar). Connect GitHub if prompted, review the resources and costs, and provide secrets in Render's secure fields. Do not paste credentials into repository files. Leave X blank if unused; the alert URL can reuse the digest URL. At least one real collection credential is needed for successful runs. If Render requires all `sync: false` fields during setup, omit optional fields where supported or remove the optional field from the Blueprint and add it later in the service environment; do not insert fake tokens.

The Blueprint uses free Postgres for initial setup. Render free databases expire and are unsuitable for permanent history; select a paid database plan before relying on this continuously. Cron compute is billed and has a monthly minimum. Review current pricing in the Dashboard before applying. Scheduled jobs have no persistent disk, so report files are ephemeral; the database and Discord carry the persistent results. The schedule runs at minute zero every hour in UTC.

After applying, check the build and first run logs. A missing collector token or total collection failure fails the run; partial provider failures are logged. Discord delivery failures also fail the run after saving the local report. No live provider or Discord verification is possible until secrets are supplied.

## Tests

```powershell
python -m unittest discover -s tests -v
```

Tests cover scoring, clustering, alert thresholds, webhook payloads, adapter normalization, deduplication, collection failure, and SQLite persistence. Set `TEST_DATABASE_URL` to a dedicated test Postgres database to enable the integration test. GitHub Actions provisions disposable Postgres, runs all tests, and builds the Docker image. Tests never invoke paid Apify actors or real Discord webhooks.

## Existing SQLite history

Set `MEME_RADAR_DB` to your existing SQLite path and `DATABASE_URL` to the destination Postgres URL, then run `python migrate_sqlite_to_postgres.py`. Keep a backup of the SQLite database. Public database connections require an explicit Render IP allow rule; the Blueprint blocks public connections by default.

## Limits

V4 clusters normalized text and supports supplied media fingerprints, OCR, and transcripts; it does not compute visual/video similarity or transcribe media. Acceleration compares engagement on recent versus older posts, not a true derivative of historical engagement. Candidate snapshots supply rank movement and score changes. Duplicate posts across searches are counted once per run. Breakout thresholds reduce repeated alerts, but delivery is not a transactional outbox: a failed webhook after snapshot persistence can affect retry alerts. DEX name matches are heuristic; API errors currently fall back to no matches. Scores are discovery signals and do not predict investment returns.

For a continuous local process, use `python run_daemon.py`. Render cron uses the single-run entry point and exits after each scheduled report.
