from ..models import MemeCandidate
from ..db import load_previous_candidate

def annotate_changes(con, candidates: list[MemeCandidate]) -> list[MemeCandidate]:
    ranked = sorted(candidates, key=lambda c: c.emergence_score, reverse=True)
    for rank, c in enumerate(ranked, 1):
        c.rank = rank
        previous = load_previous_candidate(con, c.key)
        if not previous:
            c.status = "NEW"
            continue
        c.prior_rank = previous.get("rank")
        c.prior_emergence_score = float(previous.get("emergence_score") or 0)
        c.score_delta = c.emergence_score - c.prior_emergence_score

        if c.score_delta >= 8 or (c.prior_rank and rank + 2 <= c.prior_rank):
            c.status = "SURGING"
        elif c.score_delta <= -8 or (c.prior_rank and rank >= c.prior_rank + 3):
            c.status = "COOLING"
        else:
            c.status = "STABLE"
    return ranked
