"""Public RSS/Atom feeds, with no API token or paid provider."""
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import httpx
from .base import Collector
from ..models import SocialPost


class RSSCollector(Collector):
    def __init__(self):
        self.urls = json.loads(os.getenv('RSS_FEEDS', '["https://www.reddit.com/r/memes/.rss","https://www.reddit.com/r/dankmemes/.rss"]'))

    async def collect(self):
        posts = []
        self.feed_results = []
        successes = 0
        async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers={'User-Agent': 'MemeRadar/4.0 public-feed-reader'}) as client:
            for url in self.urls:
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    root = ET.fromstring(response.content)
                    successes += 1
                    self.feed_results.append({'url': url, 'ok': True})
                    atom = '{http://www.w3.org/2005/Atom}'
                    entries = root.findall(f'{atom}entry') or root.findall('./channel/item')
                    for entry in entries[:25]:
                        title = entry.findtext(f'{atom}title') or entry.findtext('title') or ''
                        link_node = entry.find(f'{atom}link')
                        link = link_node.get('href', '') if link_node is not None else entry.findtext('link') or ''
                        pid = entry.findtext(f'{atom}id') or entry.findtext('guid') or link
                        date = entry.findtext(f'{atom}published') or entry.findtext(f'{atom}updated') or entry.findtext('pubDate')
                        try:
                            created = datetime.fromisoformat(date.replace('Z', '+00:00'))
                        except (ValueError, AttributeError):
                            created = parsedate_to_datetime(date) if date else datetime.now(timezone.utc)
                        if created.tzinfo is None:
                            created = created.replace(tzinfo=timezone.utc)
                        author = entry.findtext(f'{atom}author/{atom}name') or entry.findtext('author') or ''
                        if pid:
                            posts.append(SocialPost('rss', pid, created, author or pid, author, title, link))
                except (httpx.HTTPError, ET.ParseError, ValueError) as exc:
                    self.feed_results.append({'url': url, 'ok': False, 'error': type(exc).__name__})
                    print(f'RSS feed unavailable: {type(exc).__name__}')
        if not successes:
            raise RuntimeError('No public feeds accessible. Configure RSS_FEEDS with accessible public RSS/Atom URLs.')
        return posts
