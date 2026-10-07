import asyncio
from run_once import main

async def daemon():
    while True:
        await main()
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(daemon())
