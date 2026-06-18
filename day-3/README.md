# Day 3 — AI Agents

Three projects exploring Google ADK multi-agent workflows and Claude Code custom skills.

---

## Projects

### 1. `agents-playground/customer_support_agent`

A multi-agent customer support workflow built with **Google ADK 2.0** graph workflows.

**Architecture:**
```
User Input
    └─> input_node
            └─> classifier_agent  (SHIPPING | UNRELATED)
                    ├─> shipping_faq_agent   (answers shipping questions)
                    └─> decline_agent        (politely redirects off-topic)
```

**Setup:**
```bash
cd agents-playground/customer_support_agent
cp .env.example .env        # fill in your GOOGLE_API_KEY
pip install google-adk python-dotenv
python main.py              # interactive CLI
python test_agent.py        # run two test queries
```

---

### 2. `customer_support_web`

Flask web app wrapping the same customer support agent with a clean chat UI.

**Setup:**
```bash
cd customer_support_web
cp .env.example .env        # fill in your GOOGLE_API_KEY
pip install -r requirements.txt
python app.py
```
Then open http://localhost:5000

---

### 3. `skills-playground`

Experiments with **Claude Code custom agent skills** — reusable, declarative skills stored in `.agents/skills/`.

| Skill | Description |
|-------|-------------|
| `database-schema-validator` | Validates SQL schemas for snake_case naming, required `id` PKs, and no `DROP TABLE` statements |
| `git-commit-formatter` | Enforces Conventional Commits format (`feat`, `fix`, `docs`, etc.) |
| `json-to-pydantic` | Converts raw JSON objects into typed Pydantic model classes |
| `license-header-adder` | Prepends Apache 2.0 copyright headers to new source files |

Sample files used to test the skills are in the root of `skills-playground/`.
