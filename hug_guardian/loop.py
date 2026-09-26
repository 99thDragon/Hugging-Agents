"""The self-improvement loop: evaluate, coach, save the new version, keep it if better."""

import copy

from .coach import CoachOptimizer
from .evaluate import load_cases, run_eval, summarize
from .harness import SEED_HARNESS, HarnessFormula
from .store import Store


def split(cases):
    return ([c for c in cases if c.get("split") != "holdout"],
            [c for c in cases if c.get("split") == "holdout"])


def evaluate_and_save(store, harness, train, holdout, log=print):
    ro_train, rw_train = run_eval(harness, train)
    ro_hold, rw_hold = run_eval(harness, holdout)
    s_train, s_hold = summarize(ro_train, rw_train), summarize(ro_hold, rw_hold)
    run = {
        "harness_version": harness["version"],
        "score": s_train["score"],
        "holdout_score": s_hold["score"],
        "recall": s_train["recall"],
        "precision": s_train["precision"],
        "false_block_rate": s_train["false_block_rate"],
        "dangerous_misses": s_train["dangerous_misses"] + s_hold["dangerous_misses"],
        "failures": s_train["failures"],
        "holdout_failures": s_hold["failures"],
    }
    log(f"  v{harness['version']}: train {run['score']:.0%} | holdout {run['holdout_score']:.0%} | "
        f"recall {run['recall']:.0%} | false blocks {run['false_block_rate']:.0%} | "
        f"dangerous misses {run['dangerous_misses']}")
    return run, (ro_train, rw_train)


def better(a, b):
    """Is eval run a better than b? Train score first, holdout breaks ties."""
    return (a["score"], a["holdout_score"]) > (b["score"], b["holdout_score"])


def run_loop(rounds: int = 4, reset: bool = False, log=print):
    store = Store()
    log(f"Store: {store.backend}")
    if reset:
        store.reset()
    cases = load_cases(store)
    if not store.load_test_cases():
        store.replace_test_cases(cases)
    train, holdout = split(cases)
    log(f"Cases: {len(train)} train, {len(holdout)} holdout")

    if not store.list_harnesses():
        store.save_harness({**SEED_HARNESS, "active": True})

    best = store.active_harness()
    log(f"Evaluating starting harness v{best['version']}")
    best_run, best_trace = evaluate_and_save(store, best, train, holdout, log)
    if not any(e["harness_version"] == best["version"] for e in store.list_evals()):
        store.save_eval({**best_run, "accepted": True})

    for i in range(1, rounds + 1):
        if best_run["score"] >= 1.0:
            log("Perfect training score, stopping.")
            break
        log(f"\nRound {i}: coach is reading {len(best_run['failures'])} failures")
        formula = HarnessFormula(best)
        coach = CoachOptimizer(formula)
        coach.add_rollouts(best_trace[0])
        coach.add_rewards(best_trace[1])
        coach.step()
        coach.zero()

        new = copy.deepcopy(formula.harness)
        new.update(version=store.next_version(), parent_version=best["version"], active=False,
                   change_summary=coach.last_proposal.change_summary,
                   diagnosis=coach.last_proposal.diagnosis)
        store.save_harness(new)
        for line in new["change_summary"]:
            log(f"    - {line}")

        run, trace = evaluate_and_save(store, new, train, holdout, log)
        accepted = better(run, best_run)
        store.save_eval({**run, "accepted": accepted})
        if accepted:
            best, best_run, best_trace = new, run, trace
            store.set_active(new["version"])
            log(f"  Accepted v{new['version']} as the new best.")
        else:
            log(f"  Rejected v{new['version']}; keeping v{best['version']}.")

    log(f"\nBest: v{best['version']} train {best_run['score']:.0%}, holdout {best_run['holdout_score']:.0%}")
    return best


def diff(a: dict, b: dict) -> dict:
    ra, rb = a["rules"], b["rules"]
    ta, tb = a["allowed_tools"], b["allowed_tools"]
    pa, pb = a["context_policy"], b["context_policy"]
    return {
        "from": a["version"], "to": b["version"],
        "rules_added": [r for r in rb if r not in ra],
        "rules_removed": [r for r in ra if r not in rb],
        "tools_added": [t for t in tb if t not in ta],
        "tools_removed": [t for t in ta if t not in tb],
        "context_policy": {k: [pa.get(k), pb.get(k)] for k in pb if pa.get(k) != pb.get(k)},
        "system_prompt_changed": a["system_prompt"] != b["system_prompt"],
        "change_summary": b.get("change_summary", []),
    }
