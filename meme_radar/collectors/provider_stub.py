from .base import Collector
from ..models import SocialPost

class ProviderCollector(Collector):
    """
    Map a permitted TikTok / Instagram commercial provider into SocialPost objects.

    Keep this interface stable so the provider can be changed without rewriting
    scoring, storage or reporting.
    """
    def __init__(self, platform: str):
        self.platform = platform

    async def collect(self) -> list[SocialPost]:
        # TODO: insert provider-specific HTTP calls here.
        return []
