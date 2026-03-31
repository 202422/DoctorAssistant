import httpx
import asyncio

async def test():
    # With SSL verification disabled
    async with httpx.AsyncClient(verify=False) as client:
        r = await client.get("https://smithery.ai")
        print("Status:", r.status_code)

asyncio.run(test())