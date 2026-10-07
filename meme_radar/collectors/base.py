from abc import ABC, abstractmethod
from ..models import SocialPost

class Collector(ABC):
    @abstractmethod
    async def collect(self) -> list[SocialPost]:
        raise NotImplementedError
