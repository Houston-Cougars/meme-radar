import math
from ..models import MemeCandidate

def clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, v))

def logscore(value: float, scale: float) -> float:
    if value <= 0:
        return 0.0
    return clamp(math.log10(1 + value) / math.log10(1 + scale) * 100)

def score(c: MemeCandidate) -> MemeCandidate:
    # Cheap deterministic scoring. Tune with backtesting.
    c.velocity = c.recent_engagement
    # Cold-start candidates have no prior-hour denominator; treat them as 1.0x
    # rather than manufacturing an enormous acceleration ratio.
    c.acceleration = (c.recent_engagement / c.prior_engagement) if c.prior_engagement > 0 else 1.0

    velocity_s = logscore(c.recent_engagement, 1_000_000)
    acceleration_s = clamp((c.acceleration - 1) * 25 + 50)
    creator_s = logscore(c.creators, 1000)
    cross_s = {1: 15, 2: 65, 3: 100}.get(c.platforms, 100)
    remix_s = logscore(c.remix_count, 500)

    c.social_score = clamp(
        velocity_s * .30 +
        acceleration_s * .25 +
        creator_s * .15 +
        cross_s * .15 +
        remix_s * .15
    )

    # Crypto saturation is injected after DEX lookup.
    # The gap rewards high social signal + low current token saturation.
    c.emergence_score = clamp(c.social_score * (1 - 0.55 * c.crypto_saturation/100))
    return c

def rescore_after_crypto(c: MemeCandidate) -> MemeCandidate:
    if not c.token_matches:
        c.crypto_saturation = 0
    else:
        # Heuristic based on count/liquidity/volume, intentionally not a buy signal.
        best_liq = max((float(x.get("liquidity_usd") or 0) for x in c.token_matches), default=0)
        best_vol = max((float(x.get("volume_24h") or 0) for x in c.token_matches), default=0)
        count_s = min(35, len(c.token_matches) * 7)
        liq_s = min(35, math.log10(1+best_liq) * 6)
        vol_s = min(30, math.log10(1+best_vol) * 5)
        c.crypto_saturation = clamp(count_s + liq_s + vol_s)
    c.emergence_score = clamp(c.social_score * (1 - 0.55 * c.crypto_saturation/100))
    return c
