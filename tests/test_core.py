import unittest
from datetime import datetime, timezone
from meme_radar.models import MemeCandidate
from meme_radar.analysis.scoring import score
from meme_radar.analysis.clustering import normalize_key, similarity
from meme_radar.delivery.discord import AlertThresholds, breakout_candidates, digest_payload

class CoreTests(unittest.TestCase):
    def test_cold_start_acceleration_is_neutral(self):
        now = datetime.now(timezone.utc)
        c = MemeCandidate(
            key="jean phil", label="Jean Phil", first_seen=now, last_seen=now,
            post_count=10, creators=10, platforms=2, total_views=100000,
            total_engagement=50000, recent_engagement=50000, prior_engagement=0,
            remix_count=9,
        )
        score(c)
        self.assertEqual(c.acceleration, 1.0)

    def test_normalization_removes_noise(self):
        self.assertIn("jean", normalize_key("Jean Phil meme is everywhere"))

    def test_similarity_merges_near_duplicates(self):
        self.assertGreater(similarity("jean phil", "jean phil knows"), 0.6)

    def test_breakout_requires_crossing_or_surge(self):
        now = datetime.now(timezone.utc)
        c = MemeCandidate(
            key="test meme", label="Test Meme", first_seen=now, last_seen=now,
            post_count=100, creators=80, platforms=3, total_views=5_000_000,
            total_engagement=500_000, recent_engagement=300_000, prior_engagement=100_000,
            remix_count=50, social_score=92, crypto_saturation=8, emergence_score=88,
            acceleration=3.0, status="SURGING", prior_emergence_score=78, score_delta=10,
        )
        hits = breakout_candidates([c], AlertThresholds())
        self.assertEqual(len(hits), 1)

    def test_breakout_does_not_repeat_stable_candidate(self):
        now = datetime.now(timezone.utc)
        c = MemeCandidate(
            key="test meme", label="Test Meme", first_seen=now, last_seen=now,
            post_count=100, creators=80, platforms=3, total_views=5_000_000,
            total_engagement=500_000, recent_engagement=300_000, prior_engagement=100_000,
            remix_count=50, social_score=92, crypto_saturation=8, emergence_score=88,
            acceleration=3.0, status="STABLE", prior_emergence_score=87, score_delta=1,
        )
        hits = breakout_candidates([c], AlertThresholds())
        self.assertEqual(hits, [])

    def test_digest_payload_is_discord_safe(self):
        now = datetime.now(timezone.utc)
        c = MemeCandidate(
            key="jean phil", label="Jean Phil", first_seen=now, last_seen=now,
            post_count=20, creators=20, platforms=3, total_views=1_000_000,
            total_engagement=100_000, recent_engagement=50_000, prior_engagement=20_000,
            remix_count=10, social_score=90, crypto_saturation=10, emergence_score=85,
            acceleration=2.5, status="SURGING", rank=1, prior_rank=4,
            prior_emergence_score=70, score_delta=15,
        )
        payload = digest_payload([c], now)
        self.assertEqual(payload["username"], "Meme Radar")
        self.assertTrue(payload["embeds"])

if __name__ == "__main__":
    unittest.main()
