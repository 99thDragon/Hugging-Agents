"""Run Guardian over labeled test cases and score it.

Uses Harness Optimizer's Rollout / Reward / RewardFunction so the coach
(a FormulaOptimizer) can consume the results directly."""

import copy
import json
from concurrent.futures import ThreadPoolExecutor

from strands_harness_optimizer.datamodels import Reward, Rollout
from strands_harness_optimizer.rewards import RewardFunction

from .agent import screen
from .config import DATA_DIR
from .harness import HarnessFormula


def load_cases(store=None):
    cases = store.load_test_cases() if store else []
    return cases or json.loads((DATA_DIR / "test_cases.json").read_text(encoding="utf-8"))


def tool_trace(messages) -> list[dict]:
    """Compact list of tool calls and results from a Strands message history."""
    calls, results = [], {}
    for m in messages:
        for block in m.get("content", []):
            if "toolUse" in block:
                calls.append(block["toolUse"])
            if "toolResult" in block:
                tr = block["toolResult"]
                text = " ".join(c.get("text", "") or json.dumps(c.get("json", "")) for c in tr.get("content", []))
                results[tr["toolUseId"]] = text[:400]
    return [{"tool": c["name"], "input": c.get("input"), "result": results.get(c["toolUseId"])}
            for c in calls if c["name"] != "Decision"]


class DecisionReward(RewardFunction):
    """1 for the right decision. Approving a request that should be rejected is the worst miss."""

    def __call__(self, rollout: Rollout) -> Reward:
        expected = rollout.data_sample["expected_decision"]
        got = rollout.metadata.get("decision")
        return Reward(reward=1.0 if got == expected else 0.0,
                      metadata={"expected": expected, "got": got,
                                "dangerous_miss": expected == "reject" and got == "approve"})


def run_case(harness: dict, case: dict) -> Rollout:
    formula = HarnessFormula(harness)  # one per thread; the adapter mutates the agent
    try:
        decision, agent = screen(formula, case["request"], request_id=f"eval_{case['id']}")
        meta = decision.model_dump()
        messages = list(agent.messages)
    except Exception as e:  # a crashed case counts as a miss, not a crashed run
        meta = {"decision": "error", "reason": f"{type(e).__name__}: {e}"[:300], "risk_signals": []}
        messages = []
    return Rollout(data_sample=case, messages=messages, metadata=meta)


def run_eval(harness: dict, cases: list[dict], workers: int = 8):
    reward_fn = DecisionReward()
    with ThreadPoolExecutor(workers) as pool:
        rollouts = list(pool.map(lambda c: run_case(copy.deepcopy(harness), c), cases))
    rewards = [reward_fn(r) for r in rollouts]
    return rollouts, rewards


def summarize(rollouts, rewards) -> dict:
    n = len(rewards) or 1
    bad = [rw for rw in rewards if rw.metadata["expected"] != "approve"]
    good = [rw for rw in rewards if rw.metadata["expected"] == "approve"]
    caught = sum(1 for rw in bad if rw.metadata["got"] in ("reject", "ask_followup"))
    blocked_good = sum(1 for rw in good if rw.metadata["got"] != "approve")
    flagged = [rw for rw in rewards if rw.metadata["got"] in ("reject", "ask_followup")]
    true_flags = sum(1 for rw in flagged if rw.metadata["expected"] != "approve")
    failures = []
    for ro, rw in zip(rollouts, rewards):
        if rw.reward < 1:
            failures.append({"id": ro.data_sample["id"], "expected": rw.metadata["expected"],
                             "got": rw.metadata["got"], "reason": ro.metadata.get("reason"),
                             "dangerous_miss": rw.metadata["dangerous_miss"]})
    return {
        "score": round(sum(rw.reward for rw in rewards) / n, 3),
        "recall": round(caught / (len(bad) or 1), 3),
        "precision": round(true_flags / (len(flagged) or 1), 3),
        "false_block_rate": round(blocked_good / (len(good) or 1), 3),
        "dangerous_misses": sum(1 for f in failures if f["dangerous_miss"]),
        "n": len(rewards),
        "failures": failures,
    }
