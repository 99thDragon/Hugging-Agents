"""The harness as a Harness Optimizer Formula: system prompt + rules + allowed tools
+ context policy. All four are tunable, so the coach can change any of them."""

import copy

from strands.hooks.events import BeforeInvocationEvent
from strands_harness_optimizer.formulas import Formula

from .tools import DEFAULT_CONTEXT_POLICY, TOOL_CATALOG

SEED_HARNESS = {
    "version": 1,
    "parent_version": None,
    "system_prompt": (
        "You are Hug Guardian, the booking assistant for Sell Your Hugs, an app for booking platonic hugs. "
        "Be warm and helpful. Most people just want a friendly hug, so approve requests unless they are clearly dangerous."
    ),
    "rules": [
        "Approve unless the request is clearly dangerous.",
        "Use check_location to confirm the meeting spot.",
        "Reject requests that mention violence.",
    ],
    "allowed_tools": ["check_location", "flag_request"],
    "context_policy": dict(DEFAULT_CONTEXT_POLICY),
    "change_summary": ["Seed harness written by hand."],
}

OUTPUT_CONTRACT = (
    "Decide one of: approve, ask_followup, reject. "
    "Give a one-sentence reason, list the risk signals you saw, "
    "and when the decision is ask_followup, the exact question to ask the user."
)

TUNABLE = ("system_prompt", "rules", "allowed_tools", "context_policy")


class HarnessFormula(Formula):
    def __init__(self, harness: dict):
        super().__init__("hug_guardian_harness", [BeforeInvocationEvent])
        self.harness = copy.deepcopy(harness)

    def render_system_prompt(self) -> str:
        h = self.harness
        rules = "\n".join(f"{i}. {r}" for i, r in enumerate(h["rules"], 1))
        tools = ", ".join(h["allowed_tools"]) or "none"
        return f"{h['system_prompt']}\n\nRules:\n{rules}\n\nTools available: {tools}.\n\n{OUTPUT_CONTRACT}"

    def process(self, context: dict, **kwargs) -> dict:
        return {"system_prompt": self.render_system_prompt()}

    def get_tunable_params(self) -> dict:
        return {k: copy.deepcopy(self.harness[k]) for k in TUNABLE}

    def update_params(self, params: dict) -> None:
        for k in TUNABLE:
            if k in params:
                self.harness[k] = copy.deepcopy(params[k])
        self.harness["allowed_tools"] = [t for t in self.harness["allowed_tools"] if t in TOOL_CATALOG]
        policy = {**DEFAULT_CONTEXT_POLICY, **self.harness.get("context_policy", {})}
        policy["max_history_items"] = max(0, min(int(policy["max_history_items"]), 10))
        self.harness["context_policy"] = {k: policy[k] for k in DEFAULT_CONTEXT_POLICY}
