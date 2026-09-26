"""Hug Guardian: screens one booking request under a given harness."""

import json
import uuid
from typing import Literal, Optional

from pydantic import BaseModel, Field
from strands import Agent
from strands_harness_optimizer.adapters import apply_formulas_on_strands_agent

from .config import GUARDIAN_MODEL, make_model
from .harness import HarnessFormula
from .tools import build_tools


class Decision(BaseModel):
    decision: Literal["approve", "ask_followup", "reject"]
    reason: str = Field(description="One sentence explaining the decision.")
    risk_signals: list[str] = Field(default_factory=list, description="Short phrases for each risk noticed.")
    followup_question: Optional[str] = Field(default=None, description="Only for ask_followup: the question to ask the user.")


def build_agent(formula: HarnessFormula, request_id: str, store=None) -> Agent:
    h = formula.harness
    tools = build_tools(h["allowed_tools"], h["context_policy"], request_id, h["version"], store)
    agent = Agent(model=make_model(GUARDIAN_MODEL), tools=tools, callback_handler=None)
    # Harness Optimizer hook: sets the system prompt from the formula before each call.
    apply_formulas_on_strands_agent(agent, [formula])
    return agent


def screen(formula: HarnessFormula, request: dict, request_id: str | None = None, store=None):
    """Returns (Decision, agent) so callers can inspect the trace."""
    request_id = request_id or f"b_{uuid.uuid4().hex[:6]}"
    agent = build_agent(formula, request_id, store)
    prompt = "Screen this booking request:\n" + json.dumps(request, indent=2)
    result = agent(prompt, structured_output_model=Decision)
    decision = result.structured_output
    if decision.decision != "ask_followup":
        decision.followup_question = None
    return decision, agent
