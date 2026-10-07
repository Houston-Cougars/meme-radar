from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

import httpx

from ..models import MemeCandidate


@dataclass(frozen=True)
class AlertThresholds:
    emergence_score: float = 85.0
    social_score: float = 85.0
    max_crypto_saturation: float = 25.0
    min_platforms: int = 2
    min_acceleration: float = 1.5

    @classmethod
    def from_env(cls) -> "AlertThresholds":
        return cls(
            emergence_score=float(os.getenv("BREAKOUT_MIN_EMERGENCE", "85")),
            social_score=float(os.getenv("BREAKOUT_MIN_SOCIAL", "85")),
            max_crypto_saturation=float(os.getenv("BREAKOUT_MAX_CRYPTO_SATURATION", "25")),
            min_platforms=int(os.getenv("BREAKOUT_MIN_PLATFORMS", "2")),
            min_acceleration=float(os.getenv("BREAKOUT_MIN_ACCELERATION", "1.5")),
        )


def breakout_candidates(
    candidates: Iterable[MemeCandidate],
    thresholds: AlertThresholds,
) -> list[MemeCandidate]:
    """
    Fire only when a candidate is strong *and* this run represents a meaningful
    threshold crossing / surge. This prevents an hourly repeated alert for the
    same already-known candidate.
    """
    out: list[MemeCandidate] = []
    for c in candidates:
        qualifies = (
            c.emergence_score >= thresholds.emergence_score
            and c.social_score >= thresholds.social_score
            and c.crypto_saturation <= thresholds.max_crypto_saturation
            and c.platforms >= thresholds.min_platforms
            and c.acceleration >= thresholds.min_acceleration
        )
        if not qualifies:
            continue

        crossed = (
            c.prior_emergence_score is not None
            and c.prior_emergence_score < thresholds.emergence_score <= c.emergence_score
        )
        strong_surge = c.status == "SURGING" and c.score_delta >= 8
        if crossed or strong_surge:
            out.append(c)
    return sorted(out, key=lambda x: x.emergence_score, reverse=True)


def digest_payload(candidates: list[MemeCandidate], now: datetime) -> dict:
    ranked = sorted(candidates, key=lambda c: c.emergence_score, reverse=True)
    changed = [c for c in ranked if c.status in {"NEW", "SURGING", "COOLING"}]

    change_lines = []
    for c in changed[:6]:
        move = _movement(c)
        delta = f"{c.score_delta:+.1f}" if c.prior_emergence_score is not None else "new"
        change_lines.append(
            f"**{c.status}** · #{c.rank} {c.label} · {c.emergence_score:.0f}/100 · {move} · Δ {delta}"
        )
    if not change_lines:
        change_lines = ["No major changes since the previous run."]

    top_lines = []
    for c in ranked[:8]:
        token = "no DEX match" if not c.token_matches else f"{len(c.token_matches)} DEX match(es)"
        top_lines.append(
            f"**#{c.rank} {c.label}** — {c.emergence_score:.0f}/100 · "
            f"social {c.social_score:.0f} · crypto {c.crypto_saturation:.0f} · "
            f"{c.platforms} platforms · {token}"
        )
    if not top_lines:
        top_lines = ["No candidates passed the current threshold."]

    return {
        "username": "Meme Radar",
        "allowed_mentions": {"parse": []},
        "embeds": [
            {
                "title": "📡 Meme Radar — Hourly Digest",
                "description": "\n".join(change_lines),
                "fields": [
                    {
                        "name": "Top emerging candidates",
                        "value": "\n".join(top_lines)[:1024],
                        "inline": False,
                    }
                ],
                "footer": {"text": "Emergence score measures social signal, not expected returns."},
                "timestamp": now.isoformat(),
            }
        ],
    }


def breakout_payload(candidate: MemeCandidate, now: datetime) -> dict:
    token_text = "No obvious DEX match" if not candidate.token_matches else f"{len(candidate.token_matches)} DEX match(es) found"
    return {
        "username": "Meme Radar",
        "allowed_mentions": {"parse": []},
        "embeds": [
            {
                "title": f"🚨 BREAKOUT: {candidate.label}",
                "description": (
                    f"**Emergence:** {candidate.emergence_score:.0f}/100\n"
                    f"**Social:** {candidate.social_score:.0f}/100\n"
                    f"**Crypto saturation:** {candidate.crypto_saturation:.0f}/100\n"
                    f"**Acceleration:** {candidate.acceleration:.2f}x\n"
                    f"**Platforms:** {candidate.platforms}\n"
                    f"**Creators observed:** {candidate.creators}\n"
                    f"**Views observed:** {candidate.total_views:,}\n"
                    f"**Crypto check:** {token_text}"
                ),
                "footer": {"text": "Breakout alert = social threshold crossing; not a trade recommendation."},
                "timestamp": now.isoformat(),
            }
        ],
    }


async def post_webhook(webhook_url: str, payload: dict) -> None:
    if not webhook_url:
        return
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(webhook_url, json=payload)
        response.raise_for_status()


async def deliver_discord(candidates: list[MemeCandidate], now: datetime) -> dict:
    """Send the hourly digest and any threshold-crossing breakout alerts."""
    digest_url = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    alert_url = os.getenv("DISCORD_ALERT_WEBHOOK_URL", "").strip() or digest_url
    if not digest_url and not alert_url:
        return {"digest_sent": False, "alerts_sent": 0}

    digest_sent = False
    alerts_sent = 0

    if digest_url:
        await post_webhook(digest_url, digest_payload(candidates, now))
        digest_sent = True

    thresholds = AlertThresholds.from_env()
    for candidate in breakout_candidates(candidates, thresholds):
        await post_webhook(alert_url, breakout_payload(candidate, now))
        alerts_sent += 1

    return {"digest_sent": digest_sent, "alerts_sent": alerts_sent}


def _movement(c: MemeCandidate) -> str:
    if c.prior_rank is None:
        return "NEW"
    if c.rank is None:
        return "—"
    delta = c.prior_rank - c.rank
    if delta > 0:
        return f"↑{delta}"
    if delta < 0:
        return f"↓{abs(delta)}"
    return "—"
