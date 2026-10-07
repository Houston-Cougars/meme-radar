import os, httpx
from .base import Collector

class ApifyActorCollector(Collector):
    actor_env=""
    actor_default=""
    def __init__(self):
        self.token=os.getenv("APIFY_TOKEN","").strip()
        self.actor=os.getenv(self.actor_env,self.actor_default).replace("/","~")
        self.timeout=int(os.getenv("APIFY_TIMEOUT_SECONDS","180"))
    async def run_actor(self,payload:dict)->list[dict]:
        if not self.token: return []
        url=f"https://api.apify.com/v2/acts/{self.actor}/run-sync-get-dataset-items"
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as client:
            r=await client.post(url,headers={"Authorization":f"Bearer {self.token}"},
                                params={"clean":"true","format":"json"},json=payload)
            r.raise_for_status()
            data=r.json()
        return data if isinstance(data,list) else []
