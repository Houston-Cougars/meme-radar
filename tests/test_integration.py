import os
import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import httpx
from meme_radar.collectors.apify_base import ApifyActorCollector
from meme_radar.collectors.tiktok_apify import TikTokApifyCollector
from meme_radar.collectors.instagram_apify import InstagramApifyCollector
from meme_radar.collectors.x_api import XCollector
from meme_radar.collectors.rss import RSSCollector
from meme_radar.collectors.factory import build_collectors
from meme_radar.db import connect, save_posts, save_candidate_snapshots, load_previous_candidate
from meme_radar.models import SocialPost, MemeCandidate
from meme_radar.pipeline import run_pipeline


def post(pid='1'):
    return SocialPost('tiktok', pid, datetime.now(timezone.utc), 'creator', 'Creator', 'test meme')


def candidate(key):
    now = datetime.now(timezone.utc)
    return MemeCandidate(key, 'Test Meme', now, now, 3, 3, 2, 1000, 100, 80, 20, 2, rank=1)


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_free_feed_atom_normalization(self):
        xml = '<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>post1</id><title>Jean Phil meme</title><link href="https://example.org/post1"/><updated>2026-10-07T12:00:00Z</updated><author><name>creator</name></author></entry></feed>'
        client = AsyncMock()
        client.get.return_value = httpx.Response(200, content=xml, request=httpx.Request('GET', 'https://example.org/feed'))
        with patch.dict(os.environ, {'RSS_FEEDS': '["https://example.org/feed"]'}), patch('meme_radar.collectors.rss.httpx.AsyncClient') as factory:
            factory.return_value.__aenter__.return_value = client
            posts = await RSSCollector().collect()
        self.assertEqual((posts[0].post_id, posts[0].platform, posts[0].author_id), ('post1', 'rss', 'creator'))
        self.assertEqual(posts[0].views, 0)

    async def test_paid_credentials_do_not_enable_paid_sources(self):
        with patch.dict(os.environ, {'USE_DEMO_DATA': 'false', 'RSS_ENABLED': 'true', 'ALLOW_PAID_PROVIDERS': 'false', 'APIFY_TOKEN': 'test-only', 'X_BEARER_TOKEN': 'test-only'}):
            self.assertEqual([type(c).__name__ for c in build_collectors()], ['RSSCollector'])

    async def test_apify_uses_header_and_returns_dataset(self):
        client = AsyncMock()
        client.post.return_value = httpx.Response(200, json=[{'id': '1'}], request=httpx.Request('POST', 'https://api.apify.com'))
        with patch.dict(os.environ, {'APIFY_TOKEN': 'test-only-token'}), patch('meme_radar.collectors.apify_base.httpx.AsyncClient') as factory:
            factory.return_value.__aenter__.return_value = client
            collector = TikTokApifyCollector(terms=['meme'])
            self.assertEqual(await collector.run_actor({'searchQueries': ['meme']}), [{'id': '1'}])
        kwargs = client.post.call_args.kwargs
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer test-only-token')
        self.assertNotIn('token', kwargs['params'])

    async def test_tiktok_normalization(self):
        c = TikTokApifyCollector(terms=['meme'])
        c.run_actor = AsyncMock(return_value=[{'id': '123', 'createTime': 1700000000, 'text': 'Meme', 'playCount': 200, 'diggCount': 10, 'authorMeta': {'id': 'a', 'name': 'A'}}])
        posts = await c.collect()
        self.assertEqual((posts[0].post_id, posts[0].views, posts[0].likes), ('123', 200, 10))
        self.assertIsNotNone(posts[0].created_at.tzinfo)
        self.assertFalse(c.run_actor.call_args.args[0]['shouldDownloadVideos'])

    async def test_instagram_normalization(self):
        c = InstagramApifyCollector(terms=['meme'])
        c.run_actor = AsyncMock(return_value=[{'shortCode': 'abc', 'timestamp': '2026-01-01T00:00:00Z', 'caption': 'Meme', 'likesCount': 9, 'ownerUsername': 'creator'}])
        posts = await c.collect()
        self.assertEqual((posts[0].post_id, posts[0].likes, posts[0].author_name), ('abc', 9, 'creator'))
        self.assertEqual(c.run_actor.call_args.args[0]['searchType'], 'hashtag')

    async def test_x_normalization(self):
        client = AsyncMock()
        client.get.return_value = httpx.Response(200, json={'data': [{'id': '42', 'created_at': '2026-01-01T00:00:00Z', 'author_id': 'a', 'text': 'meme', 'public_metrics': {'like_count': 10, 'retweet_count': 3, 'quote_count': 2}}]}, request=httpx.Request('GET', 'https://api.x.com'))
        with patch.dict(os.environ, {'X_BEARER_TOKEN': 'test-only-token'}), patch('meme_radar.collectors.x_api.httpx.AsyncClient') as factory:
            factory.return_value.__aenter__.return_value = client
            posts = await XCollector(queries=['meme']).collect()
        self.assertEqual((posts[0].likes, posts[0].shares), (10, 5))
        self.assertEqual(posts[0].url, 'https://x.com/i/web/status/42')

    async def test_pipeline_deduplicates_and_keeps_partial_results(self):
        good = AsyncMock()
        good.collect.return_value = [post(), post()]
        bad = AsyncMock()
        bad.collect.side_effect = RuntimeError('provider failed')
        con = connect(':memory:')
        with patch('meme_radar.pipeline.connect', return_value=con):
            _, posts, _ = await run_pipeline([bad, good])
        self.assertEqual(len(posts), 1)
        with self.assertRaises(Exception):
            con.execute('SELECT 1')  # pipeline closes the connection

    async def test_all_collectors_failed_does_not_write_history(self):
        c = AsyncMock()
        c.collect.side_effect = RuntimeError('failed')
        with patch('meme_radar.pipeline.connect') as db:
            with self.assertRaisesRegex(RuntimeError, 'All collectors failed'):
                await run_pipeline([c])
            db.assert_not_called()


class PersistenceTests(unittest.TestCase):
    def test_sqlite_history_survives_reconnect_and_post_retries(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'DATABASE_URL': ''}):
            path = os.path.join(directory, 'history.db')
            con = connect(path)
            now = datetime.now(timezone.utc)
            save_posts(con, [post(), post()], now)
            c = candidate('sqlite-test')
            save_candidate_snapshots(con, [c], now)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM posts').fetchone()[0], 1)
            con.close()
            con = connect(path)
            self.assertEqual(load_previous_candidate(con, c.key)['rank'], 1)
            con.close()

    @unittest.skipUnless(os.getenv('TEST_DATABASE_URL'), 'dedicated test Postgres not configured')
    def test_postgres_persistence(self):
        key = 'test-' + uuid.uuid4().hex
        with patch.dict(os.environ, {'DATABASE_URL': os.environ['TEST_DATABASE_URL']}):
            con = connect()
            try:
                now = datetime.now(timezone.utc)
                p = post(key)
                save_posts(con, [p, p], now)
                save_candidate_snapshots(con, [candidate(key)], now)
                self.assertEqual(load_previous_candidate(con, key)['rank'], 1)
                with con.cursor() as cur:
                    cur.execute('SELECT COUNT(*) FROM posts WHERE post_id=%s', (key,))
                    self.assertEqual(cur.fetchone()[0], 1)
            finally:
                with con.cursor() as cur:
                    cur.execute('DELETE FROM posts WHERE post_id=%s', (key,))
                    cur.execute('DELETE FROM candidate_snapshots WHERE candidate_key=%s', (key,))
                con.commit()
                con.close()
