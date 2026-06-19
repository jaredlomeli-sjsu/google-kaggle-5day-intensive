# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0

"""
Shopping Assistant Agent — ADK 2.0 example with security gate demo.

NOTE: The hardcoded key below is a SIMULATED vulnerability for the
      Semgrep pre-commit demo. It will be caught and must be removed.
"""

import os
from typing import Dict

import google.auth
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from pydantic import BaseModel, Field

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

# ---------------------------------------------------------------------------
# Discount store (in-memory for demo)
# ---------------------------------------------------------------------------

DISCOUNT_STORE: Dict[str, bool] = {"WELCOME50": False, "SUMMER20": False}


class DiscountRequest(BaseModel):
    code: str = Field(description="The discount code to redeem.")
    user_id: str = Field(description="The ID of the user requesting redemption.")


# ---------------------------------------------------------------------------
# Agent tool
# ---------------------------------------------------------------------------

def redeem_discount(code: str, user_id: str) -> str:
    """Redeem a single-use discount code for a user.

    Args:
        code: The discount code to redeem.
        user_id: The ID of the user requesting redemption.

    Returns:
        A string indicating success or the reason for failure.
    """
    if code not in DISCOUNT_STORE:
        return "Error: Invalid discount code."
    if DISCOUNT_STORE[code]:
        return "Error: Discount code has already been redeemed."
    if not user_id or user_id.startswith("guest_"):
        return "Error: Registered user account required to redeem discounts."

    DISCOUNT_STORE[code] = True
    return f"Success: Discount code {code} redeemed successfully for user {user_id}."


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

root_agent = Agent(
    name="ShoppingHelper",
    model=Gemini(
        model="gemini-flash-latest",
    ),
    instruction=(
        "You are a helpful shopping assistant. "
        "Use your tools to redeem discount codes for users. "
        "Always confirm the user's ID before redeeming a code."
    ),
    tools=[redeem_discount],
)

app = App(name="shopping_assistant", root_agent=root_agent)
