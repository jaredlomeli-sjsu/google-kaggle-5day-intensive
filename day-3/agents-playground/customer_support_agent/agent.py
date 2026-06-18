from google.adk import Agent, Workflow, Event
from google.adk.apps import App
from pydantic import BaseModel

# Input schema to capture the query and pass it around
class UserQuery(BaseModel):
    query: str

# Node to capture the original query
def input_node(node_input: str):
    return Event(output=UserQuery(query=node_input))

# Classifier agent to classify the query
classifier_agent = Agent(
    name="classifier_agent",
    model="gemini-flash-latest",
    instruction="""
    Analyze the user's query and classify it.
    If the query is related to shipping (rates, tracking, delivery, returns), respond with the word: SHIPPING.
    If the query is unrelated to shipping, respond with the word: UNRELATED.
    Provide ONLY the classification word as your output (SHIPPING or UNRELATED), with no other text or explanation.
    """,
    output_schema=str,
)

# Router node to route based on classifier output
def routing_decision(node_input: str):
    decision = node_input.strip().upper()
    if "SHIPPING" in decision:
        return Event(route="SHIPPING")
    else:
        return Event(route="UNRELATED")

# Shipping FAQ Agent to answer shipping queries
shipping_faq_agent = Agent(
    name="shipping_faq_agent",
    model="gemini-flash-latest",
    input_schema=UserQuery,
    instruction="""
    You are a customer support representative for a shipping company.
    The user's query is: <UserQuery.query from input_node>.
    Answer their query professionally, politely, and helpfully.
    """,
    output_schema=str,
)

# Decline Agent to decline unrelated queries
decline_agent = Agent(
    name="decline_agent",
    model="gemini-flash-latest",
    input_schema=UserQuery,
    instruction="""
    You are a customer support representative for a shipping company.
    The user's query is: <UserQuery.query from input_node>.
    This query is unrelated to shipping.
    Politely decline to answer the query, explaining that you can only assist with shipping-related matters (such as shipping rates, package tracking, delivery status, or returns).
    """,
    output_schema=str,
)

# Root workflow agent
root_agent = Workflow(
    name="customer_support_workflow",
    edges=[
        ("START", input_node, classifier_agent, routing_decision),
        (routing_decision, {
            "SHIPPING": shipping_faq_agent,
            "UNRELATED": decline_agent,
        })
    ]
)

# App wrapper
app = App(
    name="customer_support_agent",
    root_agent=root_agent,
)
