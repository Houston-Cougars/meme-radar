import tempfile
import unittest
from pathlib import Path
from contextlib import closing
from unittest.mock import Mock
from unittest.mock import patch
from datetime import datetime, timezone
import sqlite3
from desktop import collect_once, validate_settings
from meme_radar.models import SocialPost


class DesktopTests(unittest.TestCase):
    def test_settings_reject_credentials_and_fast_polling(self):
        for feeds, minutes in [(['http://example.org/feed'], 60), (['https://user:pass@example.org/feed'], 60), ([], 60), (['https://example.org/feed'], 1)]:
            with self.assertRaises(ValueError):
                validate_settings(feeds, minutes)

    def test_collection_persists_unique_posts_without_paid_services(self):
        post = SocialPost('rss', 'id1', datetime.now(timezone.utc), 'creator', 'Creator', 'Test meme', 'https://example.org/post')
        with tempfile.TemporaryDirectory() as temp, patch('desktop.asyncio.run', return_value=[post, post]), patch('desktop.RSSCollector.collect', new=Mock(return_value=None)):
            result = collect_once({'feeds': ['https://example.org/feed'], 'minutes': 60}, Path(temp))
            self.assertEqual(result['count'], 1)
            with closing(sqlite3.connect(Path(temp) / 'history.db')) as con:
                self.assertEqual(con.execute('SELECT COUNT(*) FROM posts').fetchone()[0], 1)
            self.assertTrue((Path(temp) / 'last-run.json').exists())
