from datetime import datetime
from ..models import MemeCandidate

def _bar(v: float, width=14):
    n = max(0, min(width, round(v/100*width)))
    return "█"*n + "░"*(width-n)

def _movement(c: MemeCandidate) -> str:
    if c.prior_rank is None:
        return "new"
    delta = c.prior_rank - (c.rank or c.prior_rank)
    if delta > 0:
        return f"↑{delta}"
    if delta < 0:
        return f"↓{abs(delta)}"
    return "—"

def render(candidates: list[MemeCandidate], now: datetime) -> str:
    ranked = sorted(candidates, key=lambda c: c.emergence_score, reverse=True)
    lines = [
        "# MEME RADAR",
        f"Generated: {now.isoformat()}",
        "",
        "## What changed",
        "",
    ]
    changed = [c for c in ranked if c.status in {"NEW", "SURGING", "COOLING"}]
    if changed:
        for c in changed[:8]:
            sign = "+" if c.score_delta > 0 else ""
            lines.append(
                f"- **{c.status}** — {c.label}: #{c.rank} ({_movement(c)}), "
                f"score {c.emergence_score:.0f} ({sign}{c.score_delta:.1f})"
            )
    else:
        lines.append("- No major rank or score changes since the prior run.")

    lines += ["", "## Top emerging candidates", ""]
    for i, c in enumerate(ranked[:10], 1):
        token = "No obvious DEX match" if not c.token_matches else f"{len(c.token_matches)} DEX match(es)"
        lines += [
            f"### {i}. {c.label} — {c.emergence_score:.0f}/100 [{c.status}]",
            f"`{_bar(c.emergence_score)}`",
            "",
            f"- Rank movement: **{_movement(c)}**",
            f"- Social score: **{c.social_score:.0f}/100**",
            f"- Crypto saturation: **{c.crypto_saturation:.0f}/100**",
            f"- Platforms: **{c.platforms}**",
            f"- Posts observed: **{c.post_count}** from **{c.creators}** creators",
            f"- Views observed: **{c.total_views:,}**",
            f"- Engagement observed: **{c.total_engagement:,}**",
            f"- Acceleration ratio: **{c.acceleration:.2f}x**",
            f"- Crypto check: **{token}**",
            "",
        ]
        if c.token_matches:
            best = c.token_matches[0]
            lines += [
                f"Top DEX match: `{best.get('name')}` / `${best.get('symbol')}` "
                f"on {best.get('chain')} — liquidity ${float(best.get('liquidity_usd') or 0):,.0f}.",
                ""
            ]
    if not ranked:
        lines.append("No candidates passed the current clustering threshold.")
    lines += [
        "---",
        "Scores measure social emergence and crypto saturation, not expected investment returns.",
        ""
    ]
    return "\n".join(lines)
