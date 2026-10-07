import json
from dataclasses import asdict
from datetime import datetime
from ..models import MemeCandidate

def render_json(candidates: list[MemeCandidate], now: datetime) -> str:
    payload = {
        "generated_at": now.isoformat(),
        "candidates": [asdict(c) for c in sorted(candidates, key=lambda x: x.emergence_score, reverse=True)]
    }
    return json.dumps(payload, indent=2, default=str)
