# ruff: noqa
import asyncio
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from app.agent import root_agent

async def test_monstera():
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="plant-care-companion",
        session_service=session_service,
    )
    
    user_id = "test_user"
    session_id = "test_sess"
    await session_service.create_session(app_name="plant-care-companion", user_id=user_id, session_id=session_id)
    
    prompt = "Show me a care card for my Monstera."
    print("Sending prompt:", prompt)
    
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part.from_text(text=prompt)]),
    ):
        if event.content and event.content.parts:
            print(f"\n--- Event from node {event.author} ---")
            for idx, p in enumerate(event.content.parts):
                print(f"Part {idx}: text={repr(p.text)}")
                if p.inline_data:
                    print(f"Part {idx}: inline_data mime={p.inline_data.mime_type} data={repr(p.inline_data.data[:120])}")
            if event.custom_metadata:
                print("Custom Metadata:", event.custom_metadata)

if __name__ == "__main__":
    asyncio.run(test_monstera())
