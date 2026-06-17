import asyncio
from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from agent import app

load_dotenv()

async def test(query):
    print(f"\nQuery: {query}")
    print("Thinking...")
    async with InMemoryRunner(app=app) as runner:
        events = await runner.run_debug(query, quiet=True)
        for event in reversed(events):
            if event.content and event.content.parts:
                text_parts = [p.text for p in event.content.parts if p.text]
                if text_parts:
                    print(f"Agent: {''.join(text_parts)}")
                    return
    print("Agent: [No response]")

async def main():
    await test("How much is standard shipping?")
    await test("What is the weather like?")

asyncio.run(main())
