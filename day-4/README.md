# Day 4 — Domain-Specific Agents & Multi-Agent Evaluation

## Projects

### Ambient Expense Agent
An event-driven AI agent built with **ADK 2.0** that processes employee expense reports automatically. The agent uses a graph-based workflow to route expenses based on business rules — auto-approving low-value submissions and escalating high-value ones for human review.

**Workflow:**
- Parses expense amount and description from raw input
- Auto-approves expenses under $100 instantly (no LLM needed)
- Screens expenses over $100 for PII and prompt injection
- Runs an LLM-powered risk analysis via Gemini
- Flags for human review with a risk summary and recommendation

**Key Technologies:** Google ADK 2.0, Gemini, FastAPI, Pub/Sub (local simulation), Vertex AI

---

### Shopping Assistant
A conversational shopping agent that helps users find products, compare options, and make purchasing decisions through natural language.

**Key Technologies:** Google ADK 2.0, Gemini, FastAPI

---

## Key Concepts Covered
- ADK 2.0 graph-based workflow design (`Workflow`, `Edge`, `node`, `LlmAgent`)
- Event-driven agent architecture with Pub/Sub triggers
- Security screening for PII and prompt injection before LLM calls
- Multi-agent evaluation with the ADK eval framework
- Human-in-the-loop patterns using `RequestInput` nodes
