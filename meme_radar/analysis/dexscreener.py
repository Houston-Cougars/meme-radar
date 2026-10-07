import httpx

class DexScreenerClient:
    BASE = "https://api.dexscreener.com/latest/dex/search"

    async def search(self, query: str) -> list[dict]:
        if not query or query == "unknown":
            return []
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(self.BASE, params={"q": query})
            r.raise_for_status()
            pairs = r.json().get("pairs") or []
        out = []
        for p in pairs[:10]:
            base = p.get("baseToken") or {}
            out.append({
                "chain": p.get("chainId"),
                "dex": p.get("dexId"),
                "name": base.get("name"),
                "symbol": base.get("symbol"),
                "address": base.get("address"),
                "pair_address": p.get("pairAddress"),
                "liquidity_usd": (p.get("liquidity") or {}).get("usd"),
                "volume_24h": (p.get("volume") or {}).get("h24"),
                "pair_created_at": p.get("pairCreatedAt"),
                "url": p.get("url"),
            })
        return out
