import asyncio
import sys
from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from agent import app

# Ensure environment variables are loaded
load_dotenv()

# Set up standard input reading helper for async loop on Windows/Python
def get_user_input():
    print("\nYou: ", end="", flush=True)
    return sys.stdin.readline().strip()

async def main():
    async with InMemoryRunner(app=app) as runner:
        print("=" * 60)
        print("Welcome to the Shipping Customer Support Agent (ADK 2.0 Graph Workflow)")
        print("Ask anything about shipping rates, tracking, delivery, or returns.")
        print("Type 'exit' or 'quit' to end the session.")
        print("=" * 60)
        
        while True:
            try:
                # Read user input synchronously without blocking async loop completely
                user_input = await asyncio.to_thread(get_user_input)
                if user_input.lower() in ["exit", "quit"]:
                    print("Goodbye!")
                    break
                if not user_input:
                    continue
                
                print("\nThinking...")
                events = await runner.run_debug(user_input, quiet=True)
                
                # Extract the final response from the agent events
                response_found = False
                for event in reversed(events):
                    if event.content and event.content.parts:
                        text_parts = [p.text for p in event.content.parts if p.text]
                        if text_parts:
                            print(f"\nAgent: {''.join(text_parts)}")
                            response_found = True
                            break
                            
                # Fallback if no content parts were found
                if not response_found:
                    for event in reversed(events):
                        if hasattr(event, "message") and event.message:
                            print(f"\nAgent: {event.message}")
                            response_found = True
                            break
                            
                if not response_found:
                    print("\nAgent: [No response text found in the execution events]")
                    
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
