"""The coach: a Harness Optimizer FormulaOptimizer that reads Guardian's failures
and rewrites the whole harness (prompt, rules, tools, context policy).

Harness Optimizer's built-in ContrastiveReflectionOptimizer needs AWS Bedrock and
a Unix shell, so this one talks to any model via structured output instead."""

import json

from pydantic import BaseModel, Field
from strands import Agent
from strands_harness_optimizer.optimizers import FormulaOptimizer

from .config import COACH_MODEL, make_model
from .evaluate import tool_trace
from .tools import DEFAULT_CONTEXT_POLICY, TOOL_CATALOG


class ContextPolicy(BaseModel):
    max_history_items: int = Field(ge=0, le=10)
    include_reports: bool
    include_ratings: bool
    include_verification: bool


class HarnessProposal(BaseModel):
    diagnosis: str = Field(description="What patterns caused the failures, in 2-4 sentences.")
    system_prompt: str
    rules: list[str] = Field(description="Numbered-list rules, each one short, general and testable.")
    allowed_tools: list[str]
    context_policy: ContextPolicy
    change_summary: list[str] = Field(description="3-6 short bullets: what changed and why.")


COACH_PROMPT = """You are the coach for Hug Guardian, an agent that screens booking requests for a platonic hug app.
Guardian decides approve, ask_followup or reject. You improve Guardian by rewriting its harness.

You can change four things:
1. system_prompt: Guardian's role and stance.
2. rules: the safety and consent rulebook.
3. allowed_tools: which tools Guardian may call. Catalog:
{catalog}
4. context_policy: how much user history check_user_history reveals. Fields: max_history_items (0-10), include_reports, include_ratings, include_verification (account age + ID check).

Guidelines:
- Write GENERAL rules about kinds of risk. Never mention test ids, user ids, user names or specific venues.
- Fix the failures without breaking what already works. Wrongly blocking good requests also counts as a failure.
- If Guardian could not see information it needed, give it the tool or widen the context policy.
- Say when to ask_followup versus reject: fixable gaps (unclear place or time, unverified new account, unclear scope) get a question; clear danger gets a reject.
- Keep the rulebook under 15 rules."""


class CoachOptimizer(FormulaOptimizer):
    def __init__(self, formula, max_examples: int = 20):
        super().__init__(formula)
        self.max_examples = max_examples
        self.last_proposal: HarnessProposal | None = None

    def _example(self, rollout, reward) -> dict:
        case = rollout.data_sample
        return {
            "request": case["request"],
            "expected": reward.metadata["expected"],
            "guardian_decided": reward.metadata["got"],
            "guardian_reason": rollout.metadata.get("reason"),
            "why_expected": case.get("notes"),
            "tool_calls": tool_trace(rollout.messages),
        }

    def step(self) -> None:
        pairs = list(zip(self._rollouts, self._rewards))
        failures = [self._example(ro, rw) for ro, rw in pairs if rw.reward < 1][: self.max_examples]
        successes = [self._example(ro, rw) for ro, rw in pairs if rw.reward >= 1][:6]
        if not failures:
            return
        score = sum(rw.reward for _, rw in pairs) / len(pairs)
        task = (
            f"Current harness (score {score:.0%} on {len(pairs)} cases):\n"
            f"{json.dumps(self.formula.get_tunable_params(), indent=2)}\n\n"
            f"FAILURES ({len(failures)}):\n{json.dumps(failures, indent=1)}\n\n"
            f"SOME SUCCESSES (keep these working):\n{json.dumps(successes, indent=1)}\n\n"
            "Propose the next harness."
        )
        catalog = "\n".join(f"   - {k}: {v}" for k, v in TOOL_CATALOG.items())
        agent = Agent(model=make_model(COACH_MODEL, max_tokens=8000, temperature=0.3),
                      system_prompt=COACH_PROMPT.format(catalog=catalog), callback_handler=None)
        proposal: HarnessProposal = agent(task, structured_output_model=HarnessProposal).structured_output
        self.last_proposal = proposal
        self.formula.update_params({
            "system_prompt": proposal.system_prompt,
            "rules": proposal.rules,
            "allowed_tools": proposal.allowed_tools,
            "context_policy": {**DEFAULT_CONTEXT_POLICY, **proposal.context_policy.model_dump()},
        })
