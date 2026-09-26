# Hugging Agents

Hug Guardian screens booking requests for the Sell Your Hugs app and rewrites its own harness (prompt, rules, tools, context policy) to get better. Built with Strands Agents + Harness Optimizer, harness stored in MongoDB.

## Setup

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # macOS/Linux: .venv/bin/pip
cp .env.example .env                            # then fill in the keys
```

`.env`:

```
OPENROUTER_API_KEY=sk-or-...
MONGODB_URI=mongodb+srv://...     # leave empty to use a local JSON store in .localdb/
```

## Run the self-improvement loop

```bash
python scripts/loop.py --reset --rounds 3
```

Each round: evaluate on 32 train cases + 12 held-out cases, the coach reads the failures and proposes a new harness, the new version is scored and kept if it beats the best.

## Run the API for the app

```bash
uvicorn hug_guardian.api:app --host 0.0.0.0 --port 8000
```

| Endpoint | What it does |
| --- | --- |
| `POST /screen` | Screen one booking. `?version=1` screens with an older harness (for the before/after demo) |
| `GET /users` | Demo users |
| `GET /harness`, `GET /harness/versions` | Active harness, all versions |
| `GET /evals` | Score per version |
| `GET /dashboard` | Score chart page (open in a browser; add `?demo` for sample data) |
| `GET /diff?from=1&to=4` | What the coach changed |

## Layout

- `hug_guardian/agent.py` Guardian (Strands agent, structured decision)
- `hug_guardian/tools.py` check_location, check_user_history, flag_request
- `hug_guardian/harness.py` the harness as a Harness Optimizer `Formula`, plus the v1 seed
- `hug_guardian/evaluate.py` rollouts + `RewardFunction` + metrics
- `hug_guardian/coach.py` the coach, a `FormulaOptimizer`
- `hug_guardian/loop.py` the loop and version diffs
- `hug_guardian/store.py` MongoDB store (local JSON fallback)
- `data/` demo users and 44 labeled test cases
