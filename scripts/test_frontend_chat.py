# ruff: noqa
import asyncio
import json
import httpx

async def test_chat():
    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post("http://localhost:8080/chat", json={"message": "Show me a care card for my Monstera."})
        print("Status code:", res.status_code)
        print("Response JSON:", json.dumps(res.json(), indent=2))

if __name__ == "__main__":
    asyncio.run(test_chat())
