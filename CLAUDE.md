# Hug Guardian: Hackathon Project Context

Handoff notes for Claude Code. Put this file in the root of the team repo.

## The event

**MongoDB Harness Engineering & Model Wrangling Hackathon** (Sept 26, 2026)

Theme: build harnesses that adapt, remember, and run reliably over the long haul. The project must fit at least one problem statement:

- **Statement 1: Recursive Harnessing (our pick).** A self-improving agent harness that evolves its own architecture: rules, context policies, guardrails, tool access. The agent adapts its environment to a user, task, or use case.
- Statement 2: Long Horizon Engineering. Coherent memory across huge sessions, optimizing toward long-term goals from hard metrics. (Skipped: too hard to demo in a short pitch.)

Judges include Brooke, Senior Developer Advocate at AWS. Her talk pushed Kiro, Strands Agents, Harness Optimizer, and context engineering. Her core message: the harness (prompt, tools, context management) matters as much as the model. MongoDB is the host sponsor, so data lives in MongoDB.

## The idea

Build on the team's existing **Sell Your Hugs** app (https://pumptool.github.io/Hug/, repo https://github.com/pumptool/Hug). It's a PWA for booking platonic hugs: vanilla JS, 10 screens, localStorage, service worker. It has no AI.

We add **Hug Guardian**, an agent that screens booking requests and **rewrites its own rulebook** to get better.

### Agent

- Built with **Strands Agents**
- Input: a booking request (who, where, when, message, user history)
- Output: `approve` / `ask_followup` / `reject`, plus a reason
- Tools (draft): `check_location`, `check_user_history`, `flag_request`

### Harness stored in MongoDB (not hardcoded)

- System prompt
- Safety and consent rules
- Allowed tools
- Context policy (how much history the agent sees)

### Self-improvement loop

1. Run the agent on a test set of booking requests (safe and sketchy, with correct labels)
2. Score it (caught bad requests, didn't block good ones)
3. A "coach" agent reads the failures and rewrites the rulebook
4. Save the new harness version and its score to MongoDB
5. Repeat

If we use Python, use **Harness Optimizer** (`pip install strands-harness-optimizer`) for steps 2 and 3.

### MongoDB collections (draft)

- `harness_versions`: `{ version, system_prompt, rules[], tools[], context_policy, parent_version, created_at }`
- `eval_runs`: `{ harness_version, score, precision, recall, failures[], created_at }`
- `bookings`: `{ request, decision, reason, harness_version, created_at }`
- `test_cases`: `{ request, expected_decision, notes }`

### Demo

Version 1 misses obvious red flags (~60%). Run the loop. Version N catches them (~90%+). Pull the rule diffs from MongoDB to show what the agent changed about itself. The existing app is the front end: "Book" sends the request to the agent, and a small screen shows the decision and reason.

### Build list

- [x] Test set: 30 to 50 fake booking requests with labels
- [x] Strands agent + tools
- [x] MongoDB harness store, versions, scores (Atlas; local JSON fallback when MONGODB_URI is unset)
- [x] Improvement loop
- [ ] Wire the app's booking flow to the agent
- [x] Chart showing the score rising across versions (`/dashboard` on the API; `/dashboard?demo` shows sample data)

## Setup status

- Kiro bonus credits: claimed
- MongoDB Atlas: project `gameoftwo@proton.me's` in org Harness Engineering, cluster `cluster0.ir56fb` (moved from `cluster0.vhwxfdo` with `scripts/copy_db.py`). Network Access allows 0.0.0.0/0. Cloud Claude sessions cannot reach port 27017, so run Mongo steps on a laptop
- API deployed on Vercel: https://hugging-agents.vercel.app (auto-deploys on push to main; OPENROUTER_API_KEY and MONGODB_URI set in Vercel Production). `/dashboard` for scores, `/docs` to try endpoints
- Loop run 1 on Atlas: v1 75/75 (3 dangerous misses), v2 78/67, v3 91/92 (0), v4 97/83 (0). v3 is set active (best holdout)
- GitHub repo: https://github.com/99thDragon/Hugging-Agents (public)
- One teammate wants to use **LingCode** as their editor. That's fine for front-end work, but data must go in MongoDB, not LingCode's built-in Postgres. LingCode has no Python support.

## Decisions

1. **Language:** Python (Harness Optimizer for Formula / Rollout / Reward / FormulaOptimizer; custom coach since the built-in one needs Bedrock + a Unix shell)
2. **Model:** OpenRouter ($10 credit, key expires 2026-10-03). Guardian = `anthropic/claude-haiku-4.5`, coach = `anthropic/claude-sonnet-5`. Override with GUARDIAN_MODEL / COACH_MODEL in `.env`
3. **Repo:** https://github.com/99thDragon/Hugging-Agents (public). Team: 99thDragon + Sal (`vim719`)
4. **Work split + API contract:** see the PRD (Claude Docs, "Hugging Agents PRD")

## Resources

- Strands Agents: https://strandsagents.com
- Strands quickstart + Strands MCP server setup: https://strandsagents.com/docs/user-guide/sdk/quickstart/typescript/
- Harness Optimizer: https://github.com/strands-labs/harness-optimizer
- Harness Optimizer blog: https://strandsagents.com/blog/introducing-harness-optimizer/
- ARC-AGI-3 harness blog (reference pattern): https://strandsagents.com/blog/our-production-sdk-hit-99-95-on-arc-agi-3/
- Context engineering lesson: https://strandsagents.com/docs/learning/context-engineering-and-conversation-management/ (use `context_manager="auto"`)
- Agent Toolkit for AWS: https://aws.amazon.com/products/developer-tools/agent-toolkit-for-aws/
- Kiro: https://kiro.dev

## Working style

- Keep answers short and direct. No em dashes.
- The agent and the loop are what get judged. Keep app changes minimal.
- Never commit secrets. Keep keys and the MongoDB URI in `.env`, and add it to `.gitignore`.
