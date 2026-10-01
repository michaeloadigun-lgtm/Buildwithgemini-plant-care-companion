# ruff: noqa
import asyncio
import os
import time

from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.memory import VertexAiMemoryBankService
from google.genai import types

from app.agent import root_agent, PROJECT_ID, MEMORY_BANK_ID

async def run_memory_test():
    print(f"--- TESTING MEMORY BANK ({MEMORY_BANK_ID}) ---")
    
    session_service = InMemorySessionService()
    memory_service = VertexAiMemoryBankService(
        project=PROJECT_ID,
        location="us-central1",
        agent_engine_id=MEMORY_BANK_ID,
    )

    runner = Runner(
        agent=root_agent,
        app_name="plant-care-companion",
        session_service=session_service,
        memory_service=memory_service,
    )

    user_id = "test_gardener_user_1"
    
    # -------------------------------------------------------------------------
    # SESSION 1: Save durable user preferences
    # -------------------------------------------------------------------------
    session1_id = "session_001"
    await session_service.create_session(app_name="plant-care-companion", user_id=user_id, session_id=session1_id)
    print(f"\n[Session 1] User ID: {user_id} | Session ID: {session1_id}")
    
    prompt1 = "Please remember that I am a beginner gardener with a low-light indoor apartment, and I prefer low-maintenance plants that can tolerate occasional forgotten waterings."
    print(f"User > {prompt1}")

    events1 = []
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session1_id,
        new_message=types.Content(role="user", parts=[types.Part.from_text(text=prompt1)]),
    ):
        events1.append(event)
        if event.content and event.content.parts:
            for p in event.content.parts:
                if p.text:
                    print(f"Agent > {p.text}")

    print("\nWaiting 10 seconds for Memory Bank background extraction...")
    await asyncio.sleep(10)

    # -------------------------------------------------------------------------
    # SESSION 2: Start a brand NEW session and ask a question depending on memory
    # -------------------------------------------------------------------------
    session2_id = "session_002"
    await session_service.create_session(app_name="plant-care-companion", user_id=user_id, session_id=session2_id)
    print(f"\n[Session 2] User ID: {user_id} | Session ID: {session2_id} (NEW SESSION)")
    
    prompt2 = "What plant recommendations or care strategy do you have for me based on my preferences?"
    print(f"User > {prompt2}")

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session2_id,
        new_message=types.Content(role="user", parts=[types.Part.from_text(text=prompt2)]),
    ):
        if event.content and event.content.parts:
            for p in event.content.parts:
                if p.text:
                    print(f"Agent > {p.text}")

if __name__ == "__main__":
    asyncio.run(run_memory_test())
