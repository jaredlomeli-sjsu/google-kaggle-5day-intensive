import asyncio
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from agent import app as agent_app

load_dotenv()

flask_app = Flask(__name__)

async def run_agent(query: str) -> str:
    async with InMemoryRunner(app=agent_app) as runner:
        events = await runner.run_debug(query, quiet=True)
        for event in reversed(events):
            if event.content and event.content.parts:
                text_parts = [p.text for p in event.content.parts if p.text]
                if text_parts:
                    return "".join(text_parts)
    return "No response from agent."

@flask_app.route("/")
def index():
    return render_template("index.html")

@flask_app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    query = data.get("message", "").strip()
    if not query:
        return jsonify({"error": "Empty message"}), 400
    try:
        response = asyncio.run(run_agent(query))
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    flask_app.run(debug=True, port=5000)
